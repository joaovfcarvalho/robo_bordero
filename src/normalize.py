import os
import json
import csv
import logging
from pathlib import Path
from collections import defaultdict
from .claude import ClaudeClient  # Use Claude instead of Gemini

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
    """
    Calls Claude API to normalize a list of names, using existing lookups as context.

    Note: Function name kept as 'call_gemini_for_normalization' for backward compatibility,
    but now uses Claude Haiku 4.5.

    Args:
        names_to_normalize: List of names to normalize
        existing_lookup: Existing mappings to maintain consistency
        category: Type of names (time_mandante, time_visitante, estadio, competicao)
        api_key: Anthropic Claude API key

    Returns:
        Dict mapping original names to normalized names
    """
    if not names_to_normalize:
        return {}

    logging.info(f"Preparing to call Claude for category '{category}' with {len(names_to_normalize)} names.")

    try:
        # Use Claude client for normalization
        client = ClaudeClient(api_key=api_key)

        # Map category names to more user-friendly names
        category_map = {
            "time_mandante": "teams",
            "time_visitante": "teams",
            "estadio": "stadiums",
            "competicao": "competitions"
        }

        friendly_category = category_map.get(category, category)

        # Call Claude's normalize_names method
        result = client.normalize_names(
            names=names_to_normalize,
            category=friendly_category,
            existing_mappings=existing_lookup
        )

        logging.info(f"Successfully normalized {len(result)} names for category '{category}'")
        return result

    except Exception as e:
        logging.error(f"Error calling Claude for normalization: {e}")
        return {}


# Legacy function kept for compatibility - redirects to call_gemini_for_normalization
def call_claude_for_normalization_legacy(names_to_normalize: list[str], existing_lookup: dict, category: str, api_key: str) -> dict:
    """
    Legacy function - same implementation as above.
    This preserves old prompt logic for reference, but call_gemini_for_normalization should be used.

    Prompt template (for reference):
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
    # This legacy function body is kept for reference only - actual implementation uses Claude
    return {}


def refresh_lookups(csv_path: Path, lookup_dir: Path, api_key: str):
    """
    Refreshes lookup files by finding new names in the CSV and normalizing them via Claude.

    Args:
        csv_path: Path to jogos_resumo.csv
        lookup_dir: Directory containing lookup JSON files
        api_key: Anthropic Claude API key
    """
    logging.info(f"Starting lookup refresh for CSV: {csv_path}")
    if not api_key:
        logging.error("Claude API key is missing. Cannot refresh lookups.")
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

    # Call Claude for normalization and update lookups
    for category, names_list in names_to_normalize.items():
        if names_list:
            logging.info(f"Found {len(names_list)} new {category} to normalize.")
            new_mappings = call_gemini_for_normalization(names_list, lookups[category], category, api_key)
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