import { Link, NavLink, Outlet } from 'react-router-dom'

import HealthBadge from './HealthBadge'

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-10 border-b border-line bg-black/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3.5 sm:px-6">
          <Link to="/" className="flex items-center gap-2.5">
            <span className="grid size-6 place-items-center rounded-md bg-white text-[11px] font-bold text-black">
              SF
            </span>
            <span className="text-sm font-medium tracking-tight text-white">StartupForge</span>
          </Link>
          <div className="flex items-center gap-5">
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                `hidden text-sm transition sm:block ${isActive ? 'text-white' : 'text-neutral-500 hover:text-white'}`
              }
            >
              New analysis
            </NavLink>
            <HealthBadge />
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6 sm:py-14">
        <Outlet />
      </main>
      <footer className="border-t border-line">
        <p className="mx-auto max-w-6xl px-4 py-5 text-xs text-neutral-600 sm:px-6">
          AI-generated analysis. Verify important claims against the cited sources.
        </p>
      </footer>
    </div>
  )
}
