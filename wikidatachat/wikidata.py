import requests
import re
from datetime import date, datetime

def get_text_by_id(id, lang='en'):
    """
    Fetches a Wikidata entity by its ID and returns its text representation.

    Args:
        id (str): The Wikidata entity ID (e.g., 'Q42').
        lang (str): The language code for labels and descriptions.
        props (str): Properties to fetch from the entity.

    Returns:
        dict: A dictionary containing the entity's text representation.
    """
    entities = get_wikidata_entities_by_ids(id,
                                            lang=lang,
                                            props='labels|descriptions|aliases|claims')
    if id not in entities:
        return ''

    entity = clean_wikidata_entity(entities[id], lang=lang)

    text = entity['label']
    if len(entity['description']) > 0:
        text += f", {entity['description']}"
    if len(entity['aliases']) > 0:
        text += f", also known as {', '.join(entity['aliases'])}"

    if len(entity['claims']) > 0:
        properties_text = properties_to_text(entity['claims'])
        text = f"{text}. Attributes include: {properties_text}"
    else:
        text = f"{text}."

    return text

def qualifiers_to_text(qualifiers):
    """
    Converts a list of qualifiers to a readable text string.
    Qualifiers provide additional information about a claim.

    Parameters:
    - qualifiers: A dictionary of qualifiers with property IDs as keys and their values as lists.

    Returns:
    - A string representation of the qualifiers.
    """
    text = ""
    for claim in qualifiers:
        property_label = claim['property-label']
        qualifier_values = claim['values']
        if (qualifier_values is not None) and len(qualifier_values) > 0:
            if len(text) > 0:
                text += f" "

            text += f"({property_label}: {', '.join(qualifier_values)})"

        else:
            text += f"(has {property_label})"

    if len(text) > 0:
        return f" {text}"
    return ""

def properties_to_text(properties):
    """
    Converts a list of properties (claims) to a readable text string.

    Parameters:
    - properties: A dictionary of properties (claims) with property IDs as keys.

    Returns:
    - A string representation of the properties and their values.
    """
    properties_text = ""
    for claim in properties:
        property_label = claim['property-label']
        claim_values = claim['values']
        if (claim_values is not None) and (len(claim_values) > 0):

            claims_text = ""
            for claim_value in claim_values:
                if len(claims_text) > 0:
                    claims_text += f", "

                claims_text += claim_value['value']

                qualifiers = claim_value.get('qualifiers', [])
                if len(qualifiers) > 0:
                    claims_text += qualifiers_to_text(qualifiers)

            properties_text += f'\n- {property_label}: {claims_text}.'

        else:
            properties_text += f'\n- has {property_label}.'

    return properties_text

def get_wikidata_entities_by_ids(
        ids,
        lang='en',
        props='labels|descriptions|aliases|claims'
    ):

    if isinstance(ids, str):
        ids = ids.split('|')
    ids = list(set(ids)) # Ensure unique IDs

    entities_data = {}

    # Wikidata API has a limit on the number of IDs per request, typically 50 for wbgetentities.
    for chunk_idx in range(0, len(ids), 50):

        ids_chunk = ids[chunk_idx:chunk_idx+50]
        params = {
            'action': 'wbgetentities',
            'ids': "|".join(ids_chunk),
            'props': props,
            'languages': f'{lang}|mul',
            'format': 'json',
            'origin': '*',
        }
        response = requests.get(
            "https://www.wikidata.org/w/api.php?",
            params=params
        )
        response.raise_for_status()
        chunk_data = response.json().get("entities", {})
        entities_data = entities_data | chunk_data

    return entities_data

def clean_wikidata_entity(entity, lang='en'):

    # Get a list of all IDs in the entity and match them with their labels
    ids = _get_all_missing_labels_ids(entity['claims'])
    labels = get_wikidata_entities_by_ids(ids, props='labels', lang=lang)
    labels = {key: _lang_val(val['labels'], lang) \
              for key, val in labels.items()}

    clean_claims = _claims_to_json(entity['claims'], labels=labels, lang=lang)

    clean_entity = {
        'id': entity['id'],
        'label': _lang_val(entity['labels'], lang),
        'description': _lang_val(entity['descriptions'], lang),
        'aliases': entity['aliases'],
        'claims': clean_claims
    }

    return clean_entity

def _lang_val(data, lang='en'):
    return data.get(lang, data.get('mul', {})).get('value')

def _get_all_missing_labels_ids(data):
    """Get the IDs of the entity dictionary where their labels are missing.

    Args:
        data (dict or list): The data structure to search for IDs.

    Returns:
        list: The list of IDs
    """
    ids_list = set()

    if isinstance(data, dict):
        if 'property' in data:
            ids_list.add(data['property'])
        if ('unit' in data) and (data['unit'] != '1'):
            ids_list.add(data['unit'].split('/')[-1])
        if ('datatype' in data) and \
            ('datavalue' in data) and \
            (data['datatype'] in ['wikibase-item', 'wikibase-property']):
            ids_list.add(data['datavalue']['value']['id'])

        for _, value in data.items():
            ids_list = ids_list | _get_all_missing_labels_ids(value)

    elif isinstance(data, list):
        for item in data:
            ids_list = ids_list | _get_all_missing_labels_ids(item)

    return ids_list

def _time_to_text(time_data):
    """
    Converts Wikidata time data into a human-readable string.

    Parameters:
    - time_data (dict): A dictionary containing the time string, precision, and calendar model.

    Returns:
    - str: A textual representation of the time with appropriate granularity.
    """
    if time_data is None:
        return None

    time_value = time_data['time']
    precision = time_data['precision']
    calendarmodel = time_data.get('calendarmodel', 'http://www.wikidata.org/entity/Q1985786')

    # Use regex to parse the time string
    pattern = r'([+-])(\d{1,16})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z'
    match = re.match(pattern, time_value)

    if not match:
        raise ValueError("Malformed time string")

    sign, year_str, month_str, day_str, hour_str, minute_str, second_str = match.groups()
    year = int(year_str) * (1 if sign == '+' else -1)

    # Convert Julian to Gregorian if necessary
    if 'Q1985786' in calendarmodel and year > 1 and len(str(abs(year))) <= 4:  # Julian calendar
        try:
            month = 1 if month_str == '00' else int(month_str)
            day = 1 if day_str == '00' else int(day_str)
            julian_date = date(year, month, day)
            gregorian_ordinal = julian_date.toordinal() + (datetime(1582, 10, 15).toordinal() - datetime(1582, 10, 5).toordinal())
            gregorian_date = date.fromordinal(gregorian_ordinal)
            year, month, day = gregorian_date.year, gregorian_date.month, gregorian_date.day
        except ValueError:
            raise ValueError("Invalid date for Julian calendar")
    else:
        month = int(month_str) if month_str != '00' else 1
        day = int(day_str) if day_str != '00' else 1

    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    month_str = months[month - 1] if month != 0 else ''
    era = 'AD' if year > 0 else 'BC'

    if precision == 14:
        return f"{year} {month_str} {day} {hour_str}:{minute_str}:{second_str}"
    elif precision == 13:
        return f"{year} {month_str} {day} {hour_str}:{minute_str}"
    elif precision == 12:
        return f"{year} {month_str} {day} {hour_str}:00"
    elif precision == 11:
        return f"{day} {month_str} {year}"
    elif precision == 10:
        return f"{month_str} {year}"
    elif precision == 9:
        return f"{abs(year)} {era}"
    elif precision == 8:
        decade = (year // 10) * 10
        return f"{abs(decade)}s {era}"
    elif precision == 7:
        century = (abs(year) - 1) // 100 + 1
        return f"{century}th century {era}"
    elif precision == 6:
        millennium = (abs(year) - 1) // 1000 + 1
        return f"{millennium}th millennium {era}"
    elif precision == 5:
        tens_of_thousands = abs(year) // 10000
        return f"{tens_of_thousands} ten thousand years {era}"
    elif precision == 4:
        hundreds_of_thousands = abs(year) // 100000
        return f"{hundreds_of_thousands} hundred thousand years {era}"
    elif precision == 3:
        millions = abs(year) // 1000000
        return f"{millions} million years {era}"
    elif precision == 2:
        tens_of_millions = abs(year) // 10000000
        return f"{tens_of_millions} tens of millions of years {era}"
    elif precision == 1:
        hundreds_of_millions = abs(year) // 100000000
        return f"{hundreds_of_millions} hundred million years {era}"
    elif precision == 0:
        billions = abs(year) // 1000000000
        return f"{billions} billion years {era}"
    else:
        raise ValueError(f"Unknown precision value {precision}")

def _quantity_to_text(quantity_data, labels={}):
    """
    Converts Wikidata quantity data into a human-readable string.

    Parameters:
    - quantity_data (dict): A dictionary with 'amount' and optionally 'unit' (often a QID).

    Returns:
    - str: A textual representation of the quantity (e.g., "5 kg").
    """
    if quantity_data is None:
        return None

    quantity = quantity_data.get('amount')
    unit = quantity_data.get('unit')

    # 'unit' of '1' means that the value is a count and doesn't require a unit.
    if unit == '1':
        unit = None
    else:
        unit_qid = unit.rsplit('/')[-1]
        unit = labels.get(unit_qid)

    return quantity + (f" {unit}" if unit else "")

def _globalcoordinate_to_text(coor_data):
        """
        Convert a single decimal degree value to DMS with hemisphere suffix.
        `hemi_pair` is ("N", "S") for latitude or ("E", "W") for longitude.
        """

        latitude = abs(coor_data['latitude'])
        hemi = 'N' if coor_data['latitude'] >= 0 else 'S'

        degrees = int(latitude)
        minutes_full = (latitude - degrees) * 60
        minutes = int(minutes_full)
        seconds = (minutes_full - minutes) * 60

        # Round to-tenth of a second, drop trailing .0
        seconds = round(seconds, 1)
        seconds_str = f"{seconds}".rstrip("0").rstrip(".")

        lat_str = f"{degrees}°{minutes}'{seconds_str}\"{hemi}"

        longitude = abs(coor_data['longitude'])
        hemi = 'E' if coor_data['longitude'] >= 0 else 'W'

        degrees = int(longitude)
        minutes_full = (longitude - degrees) * 60
        minutes = int(minutes_full)
        seconds = (minutes_full - minutes) * 60

        # Round to-tenth of a second, drop trailing .0
        seconds = round(seconds, 1)
        seconds_str = f"{seconds}".rstrip("0").rstrip(".")

        lon_str = f"{degrees}°{minutes}'{seconds_str}\"{hemi}"

        return f'{lat_str}, {lon_str}'

def _mainsnak_to_value(mainsnak, labels={}, lang='en'):
        """
        Converts a Wikidata 'mainsnak' object into a human-readable value string. This method interprets various datatypes (e.g., wikibase-item, string, time, quantity) and returns a formatted text representation.

        Parameters:
        - mainsnak (dict): A snak object containing the value and datatype information.

        Returns:
        - str or None: A string representation of the value. If the returned string is empty, the value is discarded from the text, and If None i retured, then the whole property is discarded.
        """
        snaktype = mainsnak.get('snaktype', 'value')
        # Consider missing values
        if (snaktype != 'value'):
            return 'no value'

        # Extract the datavalue
        datavalue = mainsnak['datavalue']['value']

        # If the values is based on a language, only consider the language that matched the text representation language.
        if (type(datavalue) is dict) and \
                ('language' in datavalue) and \
                    (datavalue['language'] != lang):
            return None

        elif (mainsnak.get('datatype', '') == 'wikibase-item'):
            # return {
            #     'QID': datavalue['id'],
            #     'label': labels.get(datavalue['id'])
            # }
            return labels.get(datavalue['id'])

        elif (mainsnak.get('datatype', '') == 'wikibase-property'):
            # return {
            #     'PID': datavalue['id'],
            #     'label': labels.get(datavalue['id'])
            # }
            return labels.get(datavalue['id'])

        elif mainsnak.get('datatype', '') == 'monolingualtext':
            return datavalue.get('text')

        elif mainsnak.get('datatype', '') == 'time':
            try:
                return _time_to_text(datavalue)
            except Exception as e:
                print("Error in time formating:", e)
                return datavalue["time"]

        elif mainsnak.get('datatype', '') == 'quantity':
            try:
                return _quantity_to_text(datavalue, labels)
            except Exception as e:
                print("Error in quantity formating:", e)
                return datavalue['amount']

        elif mainsnak.get('datatype', '') == 'globe-coordinate':
            try:
                return _globalcoordinate_to_text(datavalue)
            except Exception as e:
                print("Error in global coordinates formating:", e)
                return ''

        elif mainsnak.get('datatype', '') in \
            ['wikibase-sense', 'wikibase-lexeme', 'wikibase-form', 'entity-schema']:
            return datavalue.get('id', datavalue)

        else:
            return datavalue

def _qualifiers_to_json(qualifiers, labels={}, lang='en'):
    """
    Converts qualifiers into a JSON list suitable for text generation.

    Parameters:
    - qualifiers (dict): A dictionary of qualifiers keyed by property IDs.
                            Each value is a list of qualifier statements.

    Returns:
    - list: A list of dictionaries with property labels with lists of their parsed values.
    """
    qualifier_list = []
    for pid, qualifier in qualifiers.items():
        q_value_data = []
        for q in qualifier:
            value = _mainsnak_to_value(q, labels, lang)
            if value is not None:
                q_value_data.append(value)

        if len(q_value_data) > 0:
            qualifier_list.append({
                'PID': pid,
                'property-label': labels[pid],
                'values': q_value_data
            })

    return qualifier_list

def _claims_to_json(claims, labels={}, lang='en'):
    """
    Converts a dictionary of properties (claims) into a JSON list suitable for text generation.

    Parameters:
    - properties (dict): A dictionary of claims keyed by property IDs.
        Each value is a list of claim statements for that property.

    Returns:
    - list: A list of dictionaries with property labels, and lists of
        their parsed values (and qualifiers).
    """
    properties_list = []
    for pid, claim in claims.items():
        p_value_data = []
        rank_preferred_found = False
        for c in claim:
            value = _mainsnak_to_value(c.get('mainsnak', c), labels, lang)
            qualifiers = _qualifiers_to_json(
                c.get('qualifiers', {}), labels, lang
            )
            rank = c.get('rank', 'normal').lower()

            if value is not None:
                # If a preferred rank exists, include values that are
                # only preferred. Else include only values that are
                # ranked normal (values with a depricated rank are
                # never included)
                is_rank_normal = (rank == 'normal')
                is_rank_preferred = (rank == 'preferred')
                rank_normal_condition = is_rank_normal and \
                    (not rank_preferred_found)
                if rank_normal_condition or is_rank_preferred:

                    # Found the first preferred rank
                    if (not rank_preferred_found) and \
                        is_rank_preferred:
                        rank_preferred_found = True
                        p_value_data = []

                    p_value_data.append({
                        'value': value,
                        'qualifiers': qualifiers
                    })

        if len(p_value_data) > 0:
            properties_list.append({
                'PID': pid,
                'property-label': labels[pid],
                'values': p_value_data
            })

    return properties_list