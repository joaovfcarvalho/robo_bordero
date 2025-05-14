import os
import json
import csv
import logging
from pathlib import Path
from google import genai
from google.genai import types # Ensure types is imported
from collections import defaultdict

def load_lookup(lookup_path: Path) -> dict:
    """Loads a JSON lookup file safely."""
    if lookup_path.exists():
        try:
            with open(lookup_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON from {lookup_path}. Returning empty lookup.")
            return {}
        except Exception as e:
            logging.error(f"Error loading lookup file {lookup_path}: {e}")
            return {}
    return {}

def save_lookup(lookup_path: Path, lookup_data: dict):
    """Saves a dictionary to a JSON lookup file."""
    try:
        lookup_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lookup_path, 'w', encoding='utf-8') as f:
            json.dump(lookup_data, f, ensure_ascii=False, indent=4)
        logging.info(f"Saved lookup file: {lookup_path}")
    except Exception as e:
        logging.error(f"Error saving lookup file {lookup_path}: {e}")

def get_unique_names(csv_path: Path) -> dict[str, set]:
    """Reads the jogos_resumo.csv and extracts unique names for relevant columns."""
    unique_names = defaultdict(set)
    columns_to_check = {
        'time_mandante': 2,
        'time_visitante': 3,
        'estadio': 4,
        'competicao': 5
    } # Column name to 0-based index

    if not csv_path.exists():
        logging.error(f"CSV file not found: {csv_path}")
        return dict(unique_names)

    try:
        with open(csv_path, 'r', encoding='utf-8', newline='') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader, None) # Skip header if exists (assuming it does not based on sample)
            # If header exists and you want to use names:
            # header = next(reader)
            # col_indices = {name: i for i, name in enumerate(header)}
            # columns_to_check_indices = {col: col_indices.get(col) for col in columns_to_check}

            for row in reader:
                if not row: continue # Skip empty rows
                for col_name, index in columns_to_check.items():
                    if index < len(row):
                        value = row[index].strip()
                        if value: # Avoid adding empty strings
                            unique_names[col_name].add(value)

    except FileNotFoundError:
        logging.error(f"Could not find the CSV file at {csv_path}")
    except Exception as e:
        logging.error(f"Error reading CSV file {csv_path}: {e}")

    return dict(unique_names)


def call_gemini_for_normalization(names_to_normalize: list[str], existing_lookup: dict, category: str, api_key: str) -> dict:
    """Calls the Gemini API to normalize a list of names, using existing lookups as context."""
    if not names_to_normalize:
        return {}

    logging.info(f"Preparing to call Gemini for category '{category}' with {len(names_to_normalize)} names.")
    client = genai.Client(api_key=api_key)
    model_name = "gemini-2.0-flash" # Align with common practice or your gemini.py

    prompt = f"""
    You are an expert in Brazilian football data normalization.
    Your task is to normalize the following list of {category} names based on common Brazilian football standards.

    Existing known mappings (use these as a style guide and avoid re-normalizing them differently):
    {json.dumps(existing_lookup, ensure_ascii=False, indent=2)}

    New names to normalize:
    {json.dumps(names_to_normalize, ensure_ascii=False, indent=2)}

    Normalization Rules:
    - Teams (time_mandante/time_visitante): Use Title Case. Retain state/city qualifier ONLY if needed for disambiguation (e.g., "Botafogo-RJ", "Botafogo-SP"). Remove suffixes like "SAF", "FC", "(SC)", etc., unless part of the disambiguation.
    - Stadiums (estadio): Use Title Case. Keep only the main name. Remove city/state unless needed for disambiguation (e.g., if multiple stadiums share a name).
    - Competitions (competicao): Use a consistent format like "Brasileiro - Série A", "Copa do Brasil - Profissional", "Carioca - Série A". Ensure years are removed unless they are part of a specific edition name that is fundamentally different from the general competition (e.g. "Copa do Mundo 2022" vs "Copa do Mundo"). For generic league names like "CAMPEONATO BRASILEIRO SÉRIE A 2025", it should be normalized to "Campeonato Brasileiro Série A".

    Output ONLY a valid JSON object mapping each input name from the 'New names to normalize' list to its suggested normalized form.
    The JSON object should directly map original names to normalized names. For example:
    {{
      "Original Name 1": "Normalized Name 1",
      "Original Name 2": "Normalized Name 2"
    }}
    Do not wrap the JSON in markdown (like ```json ... ```).
    """

    logging.info(f"Calling Gemini API ({model_name}) for {len(names_to_normalize)} {category} names...")
    logging.info(f"Prompt for {category}: {prompt}")

    try:
        # Use the same API pattern as analyze_pdf in src/gemini.py
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt],
            config={
                "response_mime_type": "application/json"
            }
        )

        response_text = ""
        if hasattr(response, 'text') and response.text:
            response_text = response.text.strip()
            logging.info(f"Raw response_text for {category}: {response_text}")
            logging.debug(f"Raw Gemini response text for {category}: {response_text}")

            # Attempt to parse directly, as mime_type is application/json
            try:
                normalized_map = json.loads(response_text)
                logging.info(f"Successfully received and parsed normalization map for {category}.")
                return normalized_map
            except json.JSONDecodeError as e_json:
                logging.error(f"JSON parsing error for {category}: {e_json}", exc_info=True)
                # Fallback for cases where it might still be wrapped (though ideally it shouldn't be)
                if response_text.startswith("```json"):
                    response_text_unwrapped = response_text[7:]
                    if response_text_unwrapped.endswith("```"):
                        response_text_unwrapped = response_text_unwrapped[:-3]
                    try:
                        normalized_map = json.loads(response_text_unwrapped.strip())
                        logging.info(f"Successfully parsed markdown-wrapped JSON for {category}.")
                        return normalized_map
                    except json.JSONDecodeError as e_json_unwrap:
                        logging.error(f"Failed to decode JSON response (even after unwrap) from Gemini for {category}: {e_json_unwrap}\nOriginal response text: {response.text}")
                        return {}
                else:
                    logging.error(f"Failed to decode JSON response from Gemini for {category}: {e_json}\nResponse text: {response.text}")
                    return {}
        else:
            feedback = getattr(response, 'prompt_feedback', None)
            block_reason = getattr(feedback, 'block_reason', 'N/A') if feedback else 'N/A'
            safety_ratings_str = str(getattr(feedback, 'safety_ratings', [])) if feedback else 'N/A'
            logging.warning(f"Gemini API response for {category} was empty or did not contain text. Block reason: {block_reason}. Safety ratings: {safety_ratings_str}")
            return {}

    except Exception as e:
        logging.error(f"Exception during Gemini API call for {category}: {e}", exc_info=True)
        return {}

def refresh_lookups(csv_path: Path, lookup_dir: Path, gemini_api_key: str):
    """Refreshes lookup files by finding new names in the CSV and normalizing them via Gemini."""
    logging.info(f"Starting lookup refresh for CSV: {csv_path}")
    if not gemini_api_key:
        logging.error("Gemini API key is missing. Cannot refresh lookups.")
        return

    lookup_paths = {
        "teams": lookup_dir / "teams_lookup.json",
        "stadiums": lookup_dir / "stadiums_lookup.json",
        "competitions": lookup_dir / "competitions_lookup.json",
    }

    # Load existing lookups
    lookups = {
        "teams": load_lookup(lookup_paths["teams"]),
        "stadiums": load_lookup(lookup_paths["stadiums"]),
        "competitions": load_lookup(lookup_paths["competitions"]),
    }
    logging.info(f"Existing lookups sizes: teams={len(lookups['teams'])}, stadiums={len(lookups['stadiums'])}, competitions={len(lookups['competitions'])}")

    # Get unique names from CSV
    unique_csv_names = get_unique_names(csv_path)
    logging.info(f"Extracted unique CSV names: {unique_csv_names}")

    # Consolidate team names
    all_team_names = unique_csv_names.get('time_mandante', set()).union(unique_csv_names.get('time_visitante', set()))
    logging.info(f"All unique team names combined: {all_team_names}")

    # Find names needing normalization
    names_to_normalize = {
        "teams": list(all_team_names - set(lookups["teams"].keys())),
        "stadiums": list(unique_csv_names.get('estadio', set()) - set(lookups["stadiums"].keys())),
        "competitions": list(unique_csv_names.get('competicao', set()) - set(lookups["competitions"].keys())),
    }
    for category, names in names_to_normalize.items():
        logging.info(f"Category '{category}' needs normalization for {len(names)} names: {names}")

    # Call Gemini for normalization and update lookups
    for category, names_list in names_to_normalize.items():
        if names_list:
            logging.info(f"Found {len(names_list)} new {category} to normalize.")
            new_mappings = call_gemini_for_normalization(names_list, lookups[category], category, gemini_api_key)
            logging.info(f"New mappings returned for {category}: {new_mappings}")
            if new_mappings:
                lookups[category].update(new_mappings)
                save_lookup(lookup_paths[category], lookups[category])
        else:
            logging.info(f"No new {category} found to normalize.")

    logging.info("Lookup refresh process complete.")


def write_clean_csv(raw_csv_path: Path, clean_csv_path: Path, lookup_dir: Path):
    """Writes a new CSV file with normalized names based on lookup files."""
    lookup_paths = {
        "teams": lookup_dir / "teams_lookup.json",
        "stadiums": lookup_dir / "stadiums_lookup.json",
        "competitions": lookup_dir / "competitions_lookup.json",
    }

    lookups = {
        "teams": load_lookup(lookup_paths["teams"]),
        "stadiums": load_lookup(lookup_paths["stadiums"]),
        "competitions": load_lookup(lookup_paths["competitions"]),
    }

    # Define column indices to normalize (0-based for CSV reader)
    columns_to_normalize = {
        2: "teams",        # time_mandante
        3: "teams",        # time_visitante
        4: "stadiums",     # estadio
        5: "competitions"  # competicao
    }

    if not raw_csv_path.exists():
        logging.error(f"Raw CSV file not found: {raw_csv_path}")
        return

    try:
        with open(raw_csv_path, 'r', encoding='utf-8', newline='') as infile, \
             open(clean_csv_path, 'w', encoding='utf-8', newline='') as outfile:

            reader = csv.reader(infile)
            writer = csv.writer(outfile)

            # Optional: Handle header if your CSV has one and you want to preserve it
            # header = next(reader, None) # Read the first line as header
            # if header:
            #     writer.writerow(header) # Write header to the new file

            for row_number, row in enumerate(reader, 1): # Start row_number from 1 for logging
                if not row:
                    logging.warning(f"Skipping empty row at line {row_number} in {raw_csv_path}")
                    continue
                
                new_row = list(row) # Make a mutable copy
                for index, category in columns_to_normalize.items():
                    if index < len(row):
                        original_value = row[index].strip()
                        if original_value: # Process only non-empty original values
                            # Get normalized value, fallback to original if not found in lookup
                            normalized_value = lookups[category].get(original_value, original_value)
                            new_row[index] = normalized_value
                        # else: if original_value is empty, keep the cell in new_row as is (empty)
                    else:
                        # This case handles rows that are shorter than expected.
                        logging.warning(f"Row {row_number} in {raw_csv_path} has fewer than {index + 1} columns. Column {index} for {category} normalization is out of bounds.")
                writer.writerow(new_row)
        logging.info(f"Successfully wrote normalized data to {clean_csv_path}")

    except FileNotFoundError:
         logging.error(f"Could not find the raw CSV file at {raw_csv_path}")
    except Exception as e:
        logging.error(f"Error writing clean CSV file {clean_csv_path}: {e}")