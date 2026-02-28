import { URLForm } from "@/components/url-form";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col">
      <div className="flex flex-1 flex-col items-center justify-center px-4 py-16">
        <div className="mb-12 text-center">
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight">
            <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
              YouTube → Articles
            </span>
          </h1>
          <p className="mt-6 text-lg sm:text-xl text-zinc-400 max-w-xl mx-auto leading-relaxed">
            Превратите любое YouTube видео в готовую статью для Medium, Habr или
            LinkedIn за несколько минут
          </p>
        </div>

        <URLForm />
      </div>

      <footer className="border-t border-zinc-900 py-6 text-center text-sm text-zinc-600">
        YouTube → Articles MVP
      </footer>
    </main>
  );
}
