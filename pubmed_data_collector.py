#!/usr/bin/env python3
"""
Supplement Data Collection Pipeline from PubMed API

This script extracts relevant papers about supplements from the PubMed API.
It saves the data in structured JSON format for later processing and analysis.

Usage:
    python pubmed_data_collector.py --supplement "Creatine" --max_results 100 --output "creatine_data.json"
"""

import argparse
import json
import os
import time
from datetime import datetime
import requests
from typing import Dict, List, Optional, Union, Any
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("PubMedCollector")

# Constants
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
DEFAULT_RETMAX = 20  # Default number of results per request
MAX_RETMAX = 100     # Maximum allowed by PubMed API in a single request
RATE_LIMIT_DELAY = 0.34  # To comply with NCBI's limit of 3 requests per second

class PubMedDataCollector:
    """
    Class for collecting supplement-related research data from PubMed API.
    """
    
    def __init__(self, email: str = "your_email@example.com", api_key: Optional[str] = None):
        """
        Initialize the PubMed data collector.
        
        Args:
            email: Email to identify yourself to NCBI (required by their policy)
            api_key: NCBI API key if you have one (allows higher rate limits)
        """
        self.email = email
        self.api_key = api_key
        self.search_history = {}
        
    def search_pubmed(self, 
                      supplement: str, 
                      max_results: int = 100, 
                      publication_types: List[str] = None,
                      start_year: Optional[int] = None,
                      end_year: Optional[int] = None,
                      include_abstract: bool = True,
                      include_mesh_terms: bool = True) -> Dict[str, Any]:
        """
        Search PubMed for papers related to a specific supplement.
        
        Args:
            supplement: Name of the supplement to search for
            max_results: Maximum number of results to retrieve
            publication_types: List of publication types to filter by (e.g., ["Review", "Clinical Trial"])
            start_year: Start year for the date range filter
            end_year: End year for the date range filter
            include_abstract: Whether to include abstracts in the results
            include_mesh_terms: Whether to include MeSH terms in the results
            
        Returns:
            Dictionary containing search results and metadata
        """
        # Build the search query
        query = f"{supplement}[Title] AND (therapy[Title/Abstract] OR treatment[Title/Abstract] OR intervention[Title/Abstract])"
        
        # Add publication type filters if specified
        if publication_types:
            pub_type_query = " OR ".join([f"\"{pt}\"[Publication Type]" for pt in publication_types])
            query += f" AND ({pub_type_query})"
            
        # Add date range if specified
        if start_year and end_year:
            query += f" AND {start_year}:{end_year}[pdat]"
        elif start_year:
            query += f" AND {start_year}:3000[pdat]"
        elif end_year:
            query += f" AND 1900:{end_year}[pdat]"
            
        logger.info(f"Searching PubMed for: {query}")
        
        # First, get the total count and list of PMIDs matching our search
        total_count, pmids = self._search_and_get_pmids(query, max_results)
        
        if not pmids:
            logger.warning(f"No results found for query: {query}")
            return {"supplement": supplement, "query": query, "research_count": total_count, "count": 0, "articles": []}
        
        logger.info(f"Found {len(pmids)} articles to retrieve out of {total_count} total matches. Fetching details...")
        
        # Then, fetch the full article details for these PMIDs
        articles = self._fetch_article_details(
            pmids, 
            include_abstract=include_abstract,
            include_mesh_terms=include_mesh_terms
        )
        
        # Save search history
        search_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.search_history[search_timestamp] = {
            "supplement": supplement,
            "query": query,
            "research_count": total_count,
            "retrieved_count": len(articles)
        }
        
        return {
            "supplement": supplement,
            "query": query,
            "search_date": search_timestamp,
            "research_count": total_count,
            "count": len(articles),
            "articles": articles
        }
    
    def _search_and_get_pmids(self, query: str, max_results: int) -> tuple[int, List[str]]:
        """
        Search PubMed and retrieve a list of PMIDs.
        
        Args:
            query: The search query
            max_results: Maximum number of results to retrieve
            
        Returns:
            Tuple containing total count of matching records and list of PMIDs
        """
        # First perform the search and get a WebEnv value for the search results
        search_params = {
            "db": "pubmed",
            "term": query,
            "usehistory": "y",
            "retmode": "json",
            "retmax": 0,  # Initially just get the count, not the actual results
            "tool": "SupplementResearchCollector",
            "email": self.email
        }
        
        if self.api_key:
            search_params["api_key"] = self.api_key
            
        search_url = f"{BASE_URL}esearch.fcgi"
        
        try:
            response = requests.get(search_url, params=search_params)
            response.raise_for_status()
            search_result = response.json()
            
            total_count = int(search_result["esearchresult"]["count"])
            webenv = search_result["esearchresult"]["webenv"]
            query_key = search_result["esearchresult"]["querykey"]
            
            logger.info(f"Total results found: {total_count}")
            
            if total_count == 0:
                return 0, []
                
            # Cap max_results to the actual number of results
            max_results = min(total_count, max_results)
            
            # Now fetch the PMIDs in batches
            pmids = []
            for start in range(0, max_results, MAX_RETMAX):
                # Calculate retmax for this batch
                retmax = min(MAX_RETMAX, max_results - start)
                
                fetch_params = {
                    "db": "pubmed",
                    "query_key": query_key,
                    "WebEnv": webenv,
                    "retstart": start,
                    "retmax": retmax,
                    "retmode": "json",
                    "tool": "SupplementResearchCollector",
                    "email": self.email
                }
                
                if self.api_key:
                    fetch_params["api_key"] = self.api_key
                
                logger.info(f"Fetching PMIDs batch {start} to {start + retmax}")
                fetch_response = requests.get(search_url, params=fetch_params)
                fetch_response.raise_for_status()
                
                batch_result = fetch_response.json()
                batch_pmids = batch_result["esearchresult"].get("idlist", [])
                pmids.extend(batch_pmids)
                
                logger.info(f"Retrieved {len(batch_pmids)} PMIDs in this batch")
                
                # Respect rate limits
                time.sleep(RATE_LIMIT_DELAY)
                
            return total_count, pmids
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching PubMed: {e}")
            return 0, []
    
    def _fetch_article_details(self, 
                              pmids: List[str], 
                              include_abstract: bool = True,
                              include_mesh_terms: bool = True) -> List[Dict[str, Any]]:
        """
        Fetch detailed information for a list of PubMed article IDs.
        
        Args:
            pmids: List of PubMed IDs
            include_abstract: Whether to include abstracts
            include_mesh_terms: Whether to include MeSH terms
            
        Returns:
            List of article details
        """
        if not pmids:
            return []
            
        articles = []
        # Process in batches of 100 to avoid overloading the API
        batch_size = 100
        
        for i in range(0, len(pmids), batch_size):
            batch_pmids = pmids[i:i + batch_size]
            logger.info(f"Fetching details for batch of {len(batch_pmids)} articles")
            
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(batch_pmids),
                "retmode": "xml",  # XML format provides more complete data
                "tool": "SupplementResearchCollector",
                "email": self.email
            }
            
            if self.api_key:
                fetch_params["api_key"] = self.api_key
                
            fetch_url = f"{BASE_URL}efetch.fcgi"
            
            try:
                response = requests.get(fetch_url, params=fetch_params)
                response.raise_for_status()
                
                # Parse the XML response - this is simplified and would need a proper XML parser
                # For a production system, use a dedicated XML parser like ElementTree or BeautifulSoup
                xml_content = response.text
                
                # Extract articles using helper method
                batch_articles = self._parse_pubmed_xml(
                    xml_content, 
                    include_abstract, 
                    include_mesh_terms
                )
                
                articles.extend(batch_articles)
                
                # Respect rate limits
                time.sleep(RATE_LIMIT_DELAY)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching article details: {e}")
                
        return articles
    
    def _parse_pubmed_xml(self, 
                         xml_content: str, 
                         include_abstract: bool, 
                         include_mesh_terms: bool) -> List[Dict[str, Any]]:
        """
        Parse PubMed XML response to extract article details.
        
        Note: This is a simplified parser. For production, use a proper XML parser.
        
        Args:
            xml_content: XML content from PubMed efetch
            include_abstract: Whether to include abstracts
            include_mesh_terms: Whether to include MeSH terms
            
        Returns:
            List of parsed article data
        """
        # In a real implementation, use ElementTree or BeautifulSoup for proper XML parsing
        # This is a very simplified approach for demonstration purposes
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(xml_content, 'xml')
            
            articles = []
            for article_element in soup.find_all('PubmedArticle'):
                try:
                    # Get PMID
                    pmid = article_element.find('PMID').text if article_element.find('PMID') else None
                    
                    # Get article title
                    article_title_elem = article_element.find('ArticleTitle')
                    title = article_title_elem.text if article_title_elem else None
                    
                    # Extract abstract if requested
                    abstract = None
                    if include_abstract and article_element.find('Abstract'):
                        abstract_parts = []
                        for abstract_text in article_element.find('Abstract').find_all('AbstractText'):
                            label = abstract_text.get('Label', '')
                            text = abstract_text.text
                            if label:
                                abstract_parts.append(f"{label}: {text}")
                            else:
                                abstract_parts.append(text)
                        abstract = " ".join(abstract_parts)
                    
                    # Extract publication date
                    pub_date = None
                    pub_date_elem = article_element.find('PubDate')
                    if pub_date_elem:
                        year = pub_date_elem.find('Year')
                        month = pub_date_elem.find('Month')
                        day = pub_date_elem.find('Day')
                        
                        if year:
                            pub_date = year.text
                            if month:
                                pub_date = f"{pub_date}-{month.text}"
                                if day:
                                    pub_date = f"{pub_date}-{day.text}"
                    
                    # Extract authors
                    authors = []
                    author_list = article_element.find('AuthorList')
                    if author_list:
                        for author_elem in author_list.find_all('Author'):
                            last_name = author_elem.find('LastName')
                            fore_name = author_elem.find('ForeName')
                            if last_name and fore_name:
                                authors.append(f"{fore_name.text} {last_name.text}")
                            elif last_name:
                                authors.append(last_name.text)
                    
                    # Extract journal info
                    journal_elem = article_element.find('Journal')
                    journal = None
                    if journal_elem:
                        journal_title = journal_elem.find('Title')
                        journal = journal_title.text if journal_title else None
                    
                    # Extract MeSH terms if requested
                    mesh_terms = []
                    if include_mesh_terms:
                        mesh_heading_list = article_element.find('MeshHeadingList')
                        if mesh_heading_list:
                            for mesh_heading in mesh_heading_list.find_all('MeshHeading'):
                                descriptor = mesh_heading.find('DescriptorName')
                                if descriptor:
                                    mesh_terms.append(descriptor.text)
                    
                    # Extract publication type
                    pub_types = []
                    pub_type_list = article_element.find_all('PublicationType')
                    for pub_type in pub_type_list:
                        pub_types.append(pub_type.text)
                    
                    # Construct article object
                    article_data = {
                        "pmid": pmid,
                        "title": title,
                        "authors": authors,
                        "journal": journal,
                        "publication_date": pub_date,
                        "publication_types": pub_types
                    }
                    
                    if include_abstract and abstract:
                        article_data["abstract"] = abstract
                        
                    if include_mesh_terms and mesh_terms:
                        article_data["mesh_terms"] = mesh_terms
                    
                    articles.append(article_data)
                    
                except Exception as e:
                    logger.error(f"Error parsing article: {e}")
                    continue
                    
            return articles
            
        except ImportError:
            logger.error("BeautifulSoup is required for XML parsing. Install with: pip install beautifulsoup4 lxml")
            return []
        except Exception as e:
            logger.error(f"Error parsing XML: {e}")
            return []
            
    def save_results(self, results: Dict[str, Any], output_file: str) -> bool:
        """
        Save search results to a JSON file.
        
        Args:
            results: Search results to save
            output_file: Path to the output file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Results saved to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            return False

def main():
    """Main function to run the script from command line."""
    parser = argparse.ArgumentParser(description='Collect supplement research data from PubMed')
    
    parser.add_argument('--supplement', required=True, help='Name of the supplement to search for')
    parser.add_argument('--max_results', type=int, default=100, help='Maximum number of results to retrieve')
    parser.add_argument('--output', required=True, help='Output JSON file path')
    parser.add_argument('--email', default='your_email@example.com', help='Email for PubMed API identification')
    parser.add_argument('--api_key', help='NCBI API key (optional)')
    parser.add_argument('--start_year', type=int, help='Start year for date filtering')
    parser.add_argument('--end_year', type=int, help='End year for date filtering')
    parser.add_argument('--publication_types', nargs='+', help='Publication types to filter by')
    parser.add_argument('--no_abstract', action='store_true', help='Skip including abstracts')
    parser.add_argument('--no_mesh', action='store_true', help='Skip including MeSH terms')
    
    args = parser.parse_args()
    
    # Initialize the collector
    collector = PubMedDataCollector(email=args.email, api_key=args.api_key)
    
    # Perform the search
    results = collector.search_pubmed(
        supplement=args.supplement,
        max_results=args.max_results,
        publication_types=args.publication_types,
        start_year=args.start_year,
        end_year=args.end_year,
        include_abstract=not args.no_abstract,
        include_mesh_terms=not args.no_mesh
    )
    
    # Save the results
    collector.save_results(results, args.output)
    
    # Print summary
    print(f"\nSearch summary:")
    print(f"  Supplement: {args.supplement}")
    print(f"  Total results in PubMed: {results['research_count']}")
    print(f"  Results retrieved: {results['count']}")
    print(f"  Output file: {args.output}")

if __name__ == "__main__":
    main()