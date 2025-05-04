// src/app/api/pubmed/route.ts
import { NextRequest, NextResponse } from 'next/server';

// Base URL for NCBI E-utilities
const NCBI_BASE_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/';

// Define interfaces for expected responses (optional but good practice)
interface ESearchResult {
    esearchresult?: {
        idlist: string[];
        count: string;
        retmax: string;
        retstart: string;
    };
}

interface ESummaryResult {
    result?: {
        uids: string[];
        [key: string]: any; // Represents each PMID as a key
    };
    header?: {
        type: string;
        version: string;
    };
}

interface ArticleSummary {
    uid: string; // PubMed ID (PMID)
    pubdate: string;
    title: string;
    authors: { name: string }[];
    source: string; // Journal Name
}

export async function GET(request: NextRequest) {
    const { searchParams } = new URL(request.url);
    const supplement = searchParams.get('supplement');
    const maxResultsParam = searchParams.get('maxResults') || '10'; // Default to 10 results

    if (!supplement) {
        return NextResponse.json({ error: 'Supplement query parameter is required' }, { status: 400 });
    }

    const maxResults = parseInt(maxResultsParam, 10);
    if (isNaN(maxResults) || maxResults <= 0) {
         return NextResponse.json({ error: 'Invalid maxResults parameter' }, { status: 400 });
    }

    console.log(`Workspaceing PubMed data for: ${supplement}, maxResults: ${maxResults}`);

    try {
        // Step 1: Use ESearch to find PMIDs
        const searchUrl = `${NCBI_BASE_URL}esearch.fcgi?db=pubmed&term=${encodeURIComponent(supplement)}&retmode=json&retmax=${maxResults}`;
        // console.log("ESearch URL:", searchUrl); // For debugging

        const searchResponse = await fetch(searchUrl, { cache: 'no-store' }); // Disable caching for dynamic data

        if (!searchResponse.ok) {
            console.error("ESearch Error Status:", searchResponse.status, searchResponse.statusText);
            const errorText = await searchResponse.text();
            console.error("ESearch Error Body:", errorText);
            throw new Error(`NCBI ESearch request failed: ${searchResponse.statusText}`);
        }

        const searchData: ESearchResult = await searchResponse.json();
        const pmids = searchData.esearchresult?.idlist;

        if (!pmids || pmids.length === 0) {
            console.log(`No PubMed IDs found for ${supplement}`);
            return NextResponse.json([]); // Return empty array if no results
        }

        console.log(`Found PMIDs: ${pmids.join(', ')}`);

        // Step 2: Use ESummary to get summaries for the PMIDs
        const summaryUrl = `${NCBI_BASE_URL}esummary.fcgi?db=pubmed&id=${pmids.join(',')}&retmode=json`;
        // console.log("ESummary URL:", summaryUrl); // For debugging

        const summaryResponse = await fetch(summaryUrl, { cache: 'no-store' });

         if (!summaryResponse.ok) {
            console.error("ESummary Error Status:", summaryResponse.status, summaryResponse.statusText);
            const errorText = await summaryResponse.text();
            console.error("ESummary Error Body:", errorText);
            throw new Error(`NCBI ESummary request failed: ${summaryResponse.statusText}`);
        }

        const summaryData: ESummaryResult = await summaryResponse.json();

        if (!summaryData.result) {
            console.error("ESummary Error: Invalid response structure", summaryData);
            throw new Error('Invalid response structure from NCBI ESummary');
        }

        // Step 3: Process the summaries into a cleaner format
        const articles: ArticleSummary[] = summaryData.result.uids.map(uid => {
            const articleData = summaryData.result![uid];
            return {
                uid: articleData.uid,
                pubdate: articleData.pubdate || 'N/A',
                title: articleData.title || 'No Title Available',
                authors: articleData.authors || [], // Array of { name: string }
                source: articleData.source || 'N/A', // Journal name
            };
        });

        console.log(`Successfully fetched ${articles.length} summaries.`);
        return NextResponse.json(articles);

    } catch (error) {
        console.error('Error fetching PubMed data:', error);
        const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
        return NextResponse.json({ error: 'Failed to fetch data from PubMed', details: errorMessage }, { status: 500 });
    }
}