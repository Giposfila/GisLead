import type { ReactNode } from "react";
import { ru } from "../i18n/ru";
export default function PageHeader({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <div className="eyebrow">{ru.app.workspace}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {children && <div className="header-actions">{children}</div>}
    </header>
  );
}
