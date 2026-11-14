import { Link } from "react-router-dom";
import Icon from "../components/Icon";
import PageHeader from "../components/PageHeader";
import { ru } from "../i18n/ru";

export default function Guide() {
  const t = ru.guide;
  return (
    <div className="page guide-page">
      <PageHeader title={t.title} description={t.description} />
      <div className="guide-hero">
        <div>
          <div className="eyebrow">{t.label}</div>
          <h2>{t.heading}</h2>
          <p>{t.intro}</p>
          <Link className="button button-primary" to="/settings">
            {t.action}
            <Icon name="arrow" size={17} />
          </Link>
        </div>
        <div className="guide-route" aria-hidden="true">
          <span>01</span>
          <i />
          <Icon name="pin" size={31} />
          <i />
          <span>06</span>
        </div>
      </div>
      <div className="guide-layout">
        <aside className="guide-toc">
          <div className="eyebrow">{t.contents}</div>
          {t.steps.map((step, i) => (
            <a key={step.title} href={`#step-${i + 1}`}>
              <span>{String(i + 1).padStart(2, "0")}</span>
              {step.title}
            </a>
          ))}
        </aside>
        <div className="guide-steps">
          {t.steps.map((step, i) => (
            <section
              className="guide-step"
              id={`step-${i + 1}`}
              key={step.title}
            >
              <span className="step-number">
                {String(i + 1).padStart(2, "0")}
              </span>
              <div>
                <h2>{step.title}</h2>
                <p>{step.text}</p>
                <div className="step-tip">{step.tip}</div>
                <Link to={step.to} className="text-link">
                  {step.action}
                  <Icon name="arrow" size={16} />
                </Link>
              </div>
            </section>
          ))}
          <section className="guide-note">
            <Icon name="shield" size={24} />
            <div>
              <h3>{t.noteTitle}</h3>
              <p>{t.note}</p>
            </div>
          </section>
          <section className="guide-storage">
            <h3>{t.localTitle}</h3>
            <p>{t.localText}</p>
            <pre>{t.files}</pre>
          </section>
          <section className="guide-finish">
            <div>
              <h2>{t.finish}</h2>
              <p>{t.finishText}</p>
            </div>
            <Link to="/campaigns" className="button button-primary">
              {t.finishAction}
              <Icon name="arrow" size={16} />
            </Link>
          </section>
        </div>
      </div>
    </div>
  );
}
