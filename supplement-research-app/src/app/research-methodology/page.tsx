// src/app/research-query-system/page.tsx
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';

export default function ResearchQuerySystemPage() {
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
          <CardTitle className="text-2xl font-bold">Understanding the Research Query System</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <section>
            <h2 className="text-xl font-medium mb-2">How Relevant Research is Found</h2>
            <p className="text-muted-foreground">
              When you search for a supplement or health intervention on this site, you don't just see every 
              paper that mentions it. Instead, a specialized search approach finds studies specifically 
              examining its therapeutic applications.
            </p>
          </section>
          
          <Separator />
          
          <section>
            <h2 className="text-xl font-medium mb-2">The Search Method</h2>
            <p className="text-muted-foreground">
              This system connects directly to PubMed using 
              the following query:
            </p>
            <div className="bg-gray-100 p-4 rounded-md my-4 font-mono text-sm">
              query = "{'{intervention}'}[Title] AND (therapy[Title/Abstract] OR treatment[Title/Abstract] OR intervention[Title/Abstract])"
            </div>
            <p className="text-muted-foreground">
              This means the search looks for research papers that:
            </p>
            <ol className="list-decimal pl-6 mt-2 space-y-1 text-muted-foreground">
              <li>Have your search term directly in the title (ensuring it's a primary focus)</li>
              <li>Discuss it specifically as a therapy, treatment, or intervention</li>
            </ol>
            <p className="text-muted-foreground mt-4">
              Notice the query doesn't use terms like "supplementation" because many interventions aren't supplements. For example, trying to "supplement" with acupuncture would be quite 
              detrimental (and painful)! This broader approach ensures all types of health interventions can be 
              properly researched.
            </p>
          </section>
          
          <Separator />
          
          <section>
            <h2 className="text-xl font-medium mb-2">Why This Approach Matters</h2>
            <p className="text-muted-foreground">
              While this method returns fewer total results than a basic search, the studies you see are much 
              more relevant to what you actually want to know: "Does this intervention work, and what does 
              science say about it?"
            </p>
            <p className="text-muted-foreground mt-4">
              A standard PubMed search for something like "turmeric" would return thousands of papers, including 
              many that just mention turmeric as part of something else or study its chemical properties rather 
              than its health effects.
            </p>
            <p className="text-muted-foreground mt-4">
              This focused approach filters out the noise and highlights studies that evaluate the intervention's 
              practical health applications.
            </p>
          </section>
          
          <Separator />
          
          <section>
            <h2 className="text-xl font-medium mb-2">Looking Forward</h2>
            <p className="text-muted-foreground">
              In the future, this system will likely evolve so that the 
              query can be customized based on your personal details and interests. This might be handled 
              automatically by AI or through user preferences, allowing for more personalized research results 
              that better match your specific health situation and concerns.
            </p>
          </section>
        </CardContent>
      </Card>
    </main>
  );
}