import { Link, NavLink, useLocation } from "react-router-dom";
import { ru } from "../i18n/ru";
import Icon from "./Icon";

export default function NavBar() {
  const { pathname } = useLocation();
  const links = [
    { to: "/campaigns", icon: "grid", label: ru.nav.campaigns },
    { to: "/leads", icon: "users", label: ru.nav.leads },
    { to: "/settings", icon: "settings", label: ru.nav.settings },
    { to: "/guide", icon: "book", label: ru.nav.guide },
  ] as const;
  return (
    <header className="workspace-nav">
      <NavLink
        to="/campaigns"
        className="brand"
        aria-label={`${ru.app.title} — ${ru.nav.campaigns}`}
      >
        <span className="brand-mark" aria-hidden="true">
          ✳
        </span>
        <span>
          Lead<span className="brand-light">Gis</span>
          <small>{ru.app.tagline}</small>
        </span>
      </NavLink>
      <nav aria-label={ru.app.navigation} className="main-nav">
        {links.map(({ to, icon, label }) => {
          const active =
            to === "/leads" ? pathname.endsWith("/leads") : pathname === to;
          return (
            <Link
              key={to}
              to={to}
              className={`nav-link ${active ? "active" : ""}`}
              aria-current={active ? "page" : undefined}
            >
              <Icon name={icon} size={17} />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="nav-local">
        <span className="status-dot" />
        {ru.app.localShort}
        <Icon name="shield" size={16} />
      </div>
    </header>
  );
}
