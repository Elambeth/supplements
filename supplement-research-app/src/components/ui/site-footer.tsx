export function SiteFooter() {
  const currentYear = new Date().getFullYear();
  
  return (
    <footer className="border-t py-8">
      <div className="container max-w-6xl mx-auto">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
          {/* Brand and mission */}
          <div className="space-y-3">
            <h3 className="font-medium text-lg">SupplementHub</h3>
            <p className="text-sm text-muted-foreground">
              Built with care for supplement research and education.
            </p>
          </div>
          
          {/* Quick links */}
          <div className="space-y-3">
            <h3 className="font-medium text-sm">Resources</h3>
            <div className="grid grid-cols-2 gap-2">
              <a href="/research" className="text-sm text-muted-foreground hover:underline">Research</a>
              <a href="/database" className="text-sm text-muted-foreground hover:underline">Database</a>
              <a href="/guides" className="text-sm text-muted-foreground hover:underline">Guides</a>
              <a href="/faq" className="text-sm text-muted-foreground hover:underline">FAQ</a>
              <a href="/about" className="text-sm text-muted-foreground hover:underline">About Us</a>
              <a href="/contact" className="text-sm text-muted-foreground hover:underline">Contact</a>
            </div>
          </div>
          
          {/* Disclaimer */}
          <div className="space-y-3">
            <h3 className="font-medium text-sm">Important Information</h3>
            <p className="text-sm text-muted-foreground">
              Supplement data is for informational purposes only. Not intended as medical advice. Always consult with healthcare professionals.
            </p>
          </div>
        </div>
        
        {/* Bottom bar with copyright */}
        <div className="flex flex-col md:flex-row justify-between items-center mt-8 pt-4 border-t">
          <p className="text-xs text-muted-foreground">
            © {currentYear} SupplementHub. All rights reserved.
          </p>
          <div className="flex space-x-4 mt-4 md:mt-0">
            <a href="/privacy" className="text-xs text-muted-foreground hover:underline">Privacy</a>
            <a href="/terms" className="text-xs text-muted-foreground hover:underline">Terms</a>
            <a href="/accessibility" className="text-xs text-muted-foreground hover:underline">Accessibility</a>
          </div>
        </div>
      </div>
    </footer>
  );
}