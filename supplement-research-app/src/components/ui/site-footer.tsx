export function SiteFooter() {
    return (
      <footer className="border-t py-6 md:py-0">
        <div className="container flex flex-col items-center justify-between gap-4 md:h-16 md:flex-row max-w-6xl">
          <p className="text-center text-sm leading-loose text-muted-foreground md:text-left ml-4">
            Built with care for supplement research and education.
          </p>
          <p className="text-center text-sm leading-loose text-muted-foreground md:text-right">
            Supplement data is for informational purposes only.
          </p>
        </div>
      </footer>
    );
  }