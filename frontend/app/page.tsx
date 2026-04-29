export default function Home() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight text-stone-900 mb-3">
          Cairn
        </h1>
        <p className="text-stone-500 mb-8">
          AI-powered knowledge management for developers
        </p>
        <a
          href="/login"
          className="bg-stone-900 text-white px-6 py-3 rounded-lg text-sm font-medium hover:bg-stone-700 transition-colors"
        >
          Sign In
        </a>
      </div>
    </div>
  )
}