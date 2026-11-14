import { Link, NavLink, useLocation } from "react-router-dom";
import { ru } from "../i18n/ru";
import Icon from "./Icon";

export default function NavBar() {
  const { pathname } = useLocation();
  const links = [
    { to: "/campaigns", icon: "grid", label: ru.nav.campaigns },
    { to: "/leads", icon: "users", label: ru.nav.leads },
    { to: "/settings", icon: "settings", label: ru.nav.settings },
  ] as const;
  return (
    <aside className="sidebar">
      <NavLink to="/campaigns" className="brand">
        <span className="brand-mark">
          <Icon name="pin" size={24} />
        </span>
        <span>
          Lead<span className="brand-light">Gis</span>
          <small>{ru.app.tagline}</small>
        </span>
      </NavLink>
      <div className="nav-caption">{ru.app.navigation}</div>
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
              <Icon name={icon} />
              <span>{label}</span>
              <Icon name="chevron" size={14} />
            </Link>
          );
        })}
      </nav>
      <div className="sidebar-bottom">
        <NavLink
          to="/guide"
          className={({ isActive }) =>
            `nav-link guide-link ${isActive ? "active" : ""}`
          }
        >
          <Icon name="book" />
          <span>{ru.nav.guide}</span>
          <Icon name="arrow" size={16} />
        </NavLink>
        <div className="local-note">
          <Icon name="shield" size={19} />
          <div>
            {ru.app.local}
            <small>{ru.app.localDetail}</small>
          </div>
        </div>
        <div className="version">{ru.app.version}</div>
      </div>
    </aside>
  );
}
