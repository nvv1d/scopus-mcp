from typing import Dict, List, Any, Optional

def clean_search_results(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extracts and normalizes search results from the Scopus Search API response.

    Args:
        data: The raw JSON response from Scopus API.

    Returns:
        A list of simplified dictionaries containing key article metadata.
    """
    if not data or 'search-results' not in data:
        return []
    
    entries = data['search-results'].get('entry', [])
    cleaned_entries = []
    
    for entry in entries:
        cleaned = {
            'scopus_id': entry.get('dc:identifier', '').replace('SCOPUS_ID:', ''),
            'title': entry.get('dc:title'),
            'creator': entry.get('dc:creator'),
            'publication_name': entry.get('prism:publicationName'),
            'cover_date': entry.get('prism:coverDate'),
            'doi': entry.get('prism:doi'),
            'cited_by_count': entry.get('citedby-count'),
            'aggregation_type': entry.get('prism:aggregationType'),
            'url': next((link['@href'] for link in entry.get('link', []) if link.get('@ref') == 'scopus'), None)
        }
        cleaned_entries.append(cleaned)
        
    return cleaned_entries

def clean_abstract_details(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts relevant details from the Scopus Abstract Retrieval API response.

    Args:
        data: The raw JSON response from Scopus API.

    Returns:
        A simplified dictionary containing abstract details.
    """
    # The API key can be singular or plural depending on endpoint version/context,
    # though usually 'abstracts-retrieval-response'.
    root = data.get('abstracts-retrieval-response') or data.get('abstract-retrieval-response')
    
    if not root:
        return {}

    coredata = root.get('coredata', {})
    authors_data = root.get('authors', {}).get('author', [])
    
    # Normalize authors to a list even if single author (API inconsistency)
    if isinstance(authors_data, dict):
        authors_data = [authors_data]
        
    authors = []
    for auth in authors_data:
        authors.append({
            'auth_id': auth.get('@auid'),
            'name': auth.get('ce:indexed-name'),
            'surname': auth.get('ce:surname'),
            'initials': auth.get('ce:initials')
        })

    return {
        'scopus_id': coredata.get('dc:identifier', '').replace('SCOPUS_ID:', ''),
        'doi': coredata.get('prism:doi'),
        'title': coredata.get('dc:title'),
        'description': coredata.get('dc:description'), # This is the abstract text
        'publication_name': coredata.get('prism:publicationName'),
        'cover_date': coredata.get('prism:coverDate'),
        'cited_by_count': coredata.get('citedby-count'),
        'authors': authors,
        'url': next((link['@href'] for link in coredata.get('link', []) if link.get('@ref') == 'scopus'), None)
    }

def clean_author_profile(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts details from the Scopus Author Retrieval API response.

    Args:
        data: The raw JSON response from Scopus API.

    Returns:
        A simplified dictionary containing author profile information.
    """
    if not data or 'author-retrieval-response' not in data:
        return {}
    
    root = data['author-retrieval-response']
    core = root.get('coredata', {})
    profile = root.get('author-profile', {})
    
    name_variant = profile.get('preferred-name', {})
    
    return {
        'author_id': core.get('dc:identifier', '').replace('AUTHOR_ID:', ''),
        'orcid': core.get('orcid'),
        'document_count': core.get('document-count'),
        'cited_by_count': core.get('cited-by-count'),
        'citation_count': core.get('citation-count'),
        'h_index': core.get('h-index'),
        'name': {
            'surname': name_variant.get('surname'),
            'given_name': name_variant.get('given-name'),
            'initials': name_variant.get('initials')
        },
        'current_affiliation': _extract_affiliation(profile),
        'url': next((link['@href'] for link in core.get('link', []) if link.get('@ref') == 'scopus-author'), None)
    }

def clean_author_search_results(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts the useful fields from Scopus Author Search API responses."""
    entries = data.get('search-results', {}).get('entry', []) if data else []
    if isinstance(entries, dict):
        entries = [entries]

    return [
        {
            'author_id': entry.get('dc:identifier', '').replace('AUTHOR_ID:', ''),
            'name': entry.get('preferred-name', {}).get('ce:indexed-name'),
            'document_count': entry.get('document-count'),
            'affiliation': entry.get('affiliation-current', {}).get('affiliation-name'),
            'city': entry.get('affiliation-current', {}).get('affiliation-city'),
            'country': entry.get('affiliation-current', {}).get('affiliation-country'),
        }
        for entry in entries
    ]

def _extract_affiliation(profile: Dict[str, Any]) -> Optional[str]:
    """Helper to extract current affiliation name."""
    affil = profile.get('affiliation-current', {}).get('affiliation', {})
    # Sometimes it's a list if multiple affiliations
    if isinstance(affil, list):
        affil = affil[0] if affil else {}
        
    return affil.get('ip-doc', {}).get('afdispname')
