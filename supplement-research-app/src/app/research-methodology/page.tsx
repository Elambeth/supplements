// src/app/research-methodology/page.tsx
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';

export default function ResearchMethodologyPage() {
  return (
    <main className="container max-w-4xl mx-auto px-4 py-8">
      <div className="mb-6">
        <Link href="/" className="inline-flex items-center text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to supplements
        </Link>
      </div>

      <Card className="border-none shadow-md mb-8">
        <CardHeader>
          <CardTitle className="text-2xl font-bold">Our Research Methodology</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <section>
            <h2 className="text-xl font-medium mb-2">Data Collection</h2>
            <p className="text-muted-foreground">
              We collect supplement research data directly from PubMed, the leading database of biomedical 
              literature maintained by the U.S. National Library of Medicine. Our automated system periodically 
              searches for new studies related to each supplement in our database.
            </p>
          </section>
          
          <Separator />
          
          <section>
            <h2 className="text-xl font-medium mb-2">Research Count Methodology</h2>
            <p className="text-muted-foreground">
              The research count represents the total number of published studies mentioning the supplement 
              in the title, along with treatment-related terms in the abstract. This provides a reliable 
              indicator of the volume of scientific research dedicated to studying the supplement's effects.
            </p>
          </section>
          
          <Separator />
          
          <section>
            <h2 className="text-xl font-medium mb-2">Research Ranking</h2>
            <p className="text-muted-foreground">
              Supplements are ranked based on the total number of published studies. The rank position shows 
              where a supplement stands in terms of research volume compared to all other supplements in our 
              database. The percentile indicates how a supplement compares relatively - for example, a supplement 
              in the top 10% has more research than 90% of other supplements.
            </p>
          </section>
          
          <Separator />
          
          <section>
            <h2 className="text-xl font-medium mb-2">Evidence Strength Score</h2>
            <p className="text-muted-foreground">
              The evidence strength score (from 1-10) is calculated based on several factors:
            </p>
            <ul className="list-disc pl-6 mt-2 space-y-1 text-muted-foreground">
              <li>Volume of published research</li>
              <li>Quality of studies (randomized controlled trials weighted higher)</li>
              <li>Consistency of results across studies</li>
              <li>Presence of meta-analyses and systematic reviews</li>
              <li>Recency of research</li>
            </ul>
            <p className="text-muted-foreground mt-4">
              A score of 7-10 indicates strong evidence, 4-6 indicates moderate evidence, and 1-3 indicates 
              limited evidence for the supplement's effectiveness.
            </p>
          </section>
          
          <Separator />
          
          <section>
            <h2 className="text-xl font-medium mb-2">Limitations</h2>
            <p className="text-muted-foreground">
              While we strive for accuracy, our methodology has limitations:
            </p>
            <ul className="list-disc pl-6 mt-2 space-y-1 text-muted-foreground">
              <li>Quantity of research doesn't always correlate with effectiveness</li>
              <li>Our search terms may not capture all relevant studies</li>
              <li>Negative results are equally counted in research volume</li>
              <li>Research quality varies significantly across studies</li>
            </ul>
            <p className="text-muted-foreground mt-4">
              We recommend consulting with healthcare professionals before using any supplements, regardless 
              of their research profile on our platform.
            </p>
          </section>
        </CardContent>
      </Card>
    </main>
  );
}