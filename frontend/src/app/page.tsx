import { SourceForm } from "@/components/url-form";
import { HistoryFeed } from "@/components/history-feed";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col">
      <div className="flex flex-1 flex-col items-center px-4 py-16">
        <div className="mb-12 text-center mt-16">
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight">
            <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
              Content Hub
            </span>
          </h1>
          <p className="mt-6 text-lg sm:text-xl text-zinc-400 max-w-xl mx-auto leading-relaxed">
            Превратите YouTube видео, статью, PDF или EPUB в готовый контент для
            Medium, Habr, LinkedIn, ResearchGate и видео-промпт
          </p>
        </div>

        <SourceForm />
        <HistoryFeed />
      </div>

      <footer className="border-t border-zinc-900 py-6 text-center text-sm text-zinc-600">
        Content Hub v0.2
      </footer>
    </main>
  );
}
