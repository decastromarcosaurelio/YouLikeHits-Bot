const FEATURES = [
  {
    icon: "🔗",
    title: "Website Views",
    desc: "Automatically visit websites to earn points. Handles timers and tab management.",
  },
  {
    icon: "▶",
    title: "YouTube Views",
    desc: "Watch YouTube videos for points. Auto-submits after the timer; pauses for you when a captcha appears.",
  },
  {
    icon: "🎵",
    title: "SoundCloud Plays",
    desc: "Play SoundCloud tracks to earn points. Fully automated with random delays.",
  },
  {
    icon: "🎁",
    title: "Daily Bonus",
    desc: "Auto-claim daily bonus points when available. Never miss a reward.",
  },
  {
    icon: "🔄",
    title: "Master Loop",
    desc: "Cycles through all tasks automatically. Set it and forget it.",
  },
  {
    icon: "🖥",
    title: "GUI + CLI",
    desc: "Modern customtkinter GUI or traditional CLI menu. Your choice.",
  },
];

const PLATFORMS = ["Website Views", "YouTube Views", "SoundCloud Plays", "Daily Bonus"];

export default function Home() {
  return (
    <main className="min-h-screen">
      {/* Hero */}
      <section className="relative overflow-hidden px-6 py-24 text-center">
        <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-blue-900/20 via-transparent to-transparent" />
        <h1 className="mb-4 text-5xl font-bold tracking-tight sm:text-6xl">
          <span className="bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
            YouLikeHits
          </span>{" "}
          Autobot
        </h1>
        <p className="mx-auto mb-8 max-w-2xl text-lg text-gray-400">
          Free, open-source Python bot that automates social media exchange
          tasks on YouLikeHits: website views, YouTube views, SoundCloud plays
          and the daily bonus. Works on XFCE, KDE Plasma, and any Linux desktop.
        </p>
        <div className="flex flex-wrap justify-center gap-4">
          <a
            href="https://github.com/techengineerworkstation/YouLikeHits-Bot"
            className="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white transition hover:bg-blue-500"
          >
            View on GitHub
          </a>
          <a
            href="#features"
            className="rounded-lg border border-gray-700 px-6 py-3 font-semibold text-gray-300 transition hover:border-gray-500 hover:text-white"
          >
            Learn More
          </a>
        </div>
      </section>

      {/* Supported Platforms */}
      <section className="border-t border-gray-800 px-6 py-16">
        <h2 className="mb-8 text-center text-2xl font-bold">
          Automated Tasks
        </h2>
        <div className="mx-auto flex max-w-3xl flex-wrap justify-center gap-3">
          {PLATFORMS.map((p) => (
            <span
              key={p}
              className="rounded-full border border-gray-700 bg-gray-800/50 px-4 py-2 text-sm text-gray-300"
            >
              {p}
            </span>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="border-t border-gray-800 px-6 py-20">
        <h2 className="mb-12 text-center text-3xl font-bold">Features</h2>
        <div className="mx-auto grid max-w-5xl gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="rounded-xl border border-gray-800 bg-gray-900/50 p-6 transition hover:border-blue-600/50"
            >
              <div className="mb-3 text-3xl">{f.icon}</div>
              <h3 className="mb-2 text-lg font-semibold">{f.title}</h3>
              <p className="text-sm text-gray-400">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Quick Start */}
      <section className="border-t border-gray-800 px-6 py-20">
        <h2 className="mb-8 text-center text-3xl font-bold">Quick Start</h2>
        <div className="mx-auto max-w-2xl space-y-4">
          <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-6">
            <h3 className="mb-2 font-mono text-sm text-blue-400">
              1. Clone &amp; install
            </h3>
            <pre className="overflow-x-auto rounded-lg bg-gray-950 p-4 text-sm text-gray-300">
              <code>{`git clone https://github.com/techengineerworkstation/YouLikeHits-Bot.git
cd YouLikeHits-Bot
./run.sh`}</code>
            </pre>
          </div>
          <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-6">
            <h3 className="mb-2 font-mono text-sm text-blue-400">
              2. Login
            </h3>
            <p className="text-sm text-gray-400">
              Click &quot;Setup Browser&quot; in the GUI. Log in to YouLikeHits
              in the Chrome window that opens, and keep that window open.
            </p>
          </div>
          <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-6">
            <h3 className="mb-2 font-mono text-sm text-blue-400">
              3. Start earning
            </h3>
            <p className="text-sm text-gray-400">
              Start one loop: Website Views, YouTube, SoundCloud, Daily Bonus,
              or the Master Loop to cycle through all of them. Stop responds
              within a second.
            </p>
          </div>
          <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-6">
            <h3 className="mb-2 font-mono text-sm text-blue-400">
              Optional: Install to app menu
            </h3>
            <pre className="overflow-x-auto rounded-lg bg-gray-950 p-4 text-sm text-gray-300">
              <code>./install.sh</code>
            </pre>
            <p className="mt-2 text-sm text-gray-400">
              Adds a .desktop file for XFCE and KDE Plasma application menus.
            </p>
          </div>
        </div>
      </section>

      {/* Requirements */}
      <section className="border-t border-gray-800 px-6 py-16">
        <h2 className="mb-8 text-center text-2xl font-bold">Requirements</h2>
        <div className="mx-auto flex max-w-2xl flex-wrap justify-center gap-4 text-sm text-gray-400">
          <span className="rounded-lg border border-gray-800 bg-gray-900/50 px-4 py-2">
            Python 3.10+
          </span>
          <span className="rounded-lg border border-gray-800 bg-gray-900/50 px-4 py-2">
            Google Chrome
          </span>
          <span className="rounded-lg border border-gray-800 bg-gray-900/50 px-4 py-2">
            Linux (XFCE / Plasma / GNOME)
          </span>
          <span className="rounded-lg border border-gray-800 bg-gray-900/50 px-4 py-2">
            ~200 MB disk
          </span>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 px-6 py-8 text-center text-sm text-gray-500">
        YouLikeHits Autobot &mdash; Not affiliated with YouLikeHits.com.
        Use responsibly.
      </footer>
    </main>
  );
}
