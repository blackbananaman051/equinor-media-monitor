import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _build_html(report, alert_messages=None):
    sentiment  = report.get("market_sentiment", "neutral")
    oil_trend  = report.get("oil_price_trend",  "stable")
    sent_color = {"positive": "#059669", "negative": "#dc2626", "neutral": "#64748b"}[sentiment]
    arrow      = {"rising": "↑", "falling": "↓", "stable": "→"}[oil_trend]
    trend_col  = {"rising": "#059669", "falling": "#dc2626", "stable": "#64748b"}[oil_trend]

    alert_banner = ""
    if alert_messages:
        for a in alert_messages:
            bg = "#fef2f2" if a["level"] == "critical" else "#fffbeb"
            bc = "#dc2626"  if a["level"] == "critical" else "#d97706"
            alert_banner += f'<div style="background:{bg};border-left:4px solid {bc};padding:12px 16px;margin-bottom:12px;font-size:13px;color:#0f172a;">{a["message"]}</div>'

    articles_rows = ""
    for a in (report.get("articles") or []):
        if a.get("equinor_relevance") not in ("high", "medium"):
            continue
        rel   = a.get("equinor_relevance", "low")
        r_col = "#2563eb" if rel == "high" else "#d97706"
        articles_rows += f"""
        <tr><td style="padding:10px 0;border-bottom:1px solid #e2e8f0;vertical-align:top;">
          <a href="{a.get('url','#')}" style="font-weight:600;color:#0f172a;text-decoration:none;font-size:13px;">{a.get('title','')[:100]}</a>
          <div style="font-size:12px;color:#475569;margin-top:4px;line-height:1.5;">{(a.get('summary') or '')[:160]}…</div>
          <div style="margin-top:5px;">
            <span style="background:{r_col};color:white;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;">{rel.upper()}</span>
            <span style="color:#94a3b8;font-size:11px;margin-left:6px;">{a.get('source','')}</span>
          </div>
        </td></tr>"""

    themes = "".join(
        f'<span style="background:#eff6ff;color:#2563eb;border:1px solid #bfdbfe;border-radius:12px;padding:3px 10px;font-size:11px;margin:3px 2px;display:inline-block;">{t}</span>'
        for t in (report.get("key_themes") or [])
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f1f4f8;margin:0;padding:20px;">
<div style="max-width:640px;margin:0 auto;background:white;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0;">

  <div style="background:#0d1b2a;padding:24px 32px;color:white;">
    <div style="display:inline-block;background:#2563eb;padding:4px 12px;border-radius:6px;font-size:11px;font-weight:700;letter-spacing:0.05em;margin-bottom:12px;text-transform:uppercase;">Weekly Intelligence Brief</div>
    <h1 style="font-size:20px;font-weight:800;margin:0 0 4px;">Norwegian Oil Industry</h1>
    <div style="font-size:13px;opacity:0.55;">{report.get('date','')}</div>
  </div>

  <div style="padding:20px 32px 0;">
    {alert_banner}
  </div>

  <div style="padding:0 32px 16px;display:flex;gap:16px;border-bottom:1px solid #e2e8f0;flex-wrap:wrap;">
    <div style="flex:1;min-width:100px;text-align:center;padding:16px 0;">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:#64748b;margin-bottom:4px;">Sentiment</div>
      <div style="font-size:16px;font-weight:800;color:{sent_color};">{sentiment.upper()}</div>
    </div>
    <div style="flex:1;min-width:100px;text-align:center;padding:16px 0;">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:#64748b;margin-bottom:4px;">Oil Trend</div>
      <div style="font-size:16px;font-weight:800;color:{trend_col};">{arrow} {oil_trend.upper()}</div>
    </div>
    <div style="flex:1;min-width:100px;text-align:center;padding:16px 0;">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:#64748b;margin-bottom:4px;">Articles</div>
      <div style="font-size:16px;font-weight:800;color:#0f172a;">{report.get('articles_count',0)}</div>
    </div>
    <div style="flex:1;min-width:100px;text-align:center;padding:16px 0;">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:#64748b;margin-bottom:4px;">Relevant</div>
      <div style="font-size:16px;font-weight:800;color:#0f172a;">{report.get('relevant_count',0)}</div>
    </div>
  </div>

  <div style="padding:24px 32px;border-bottom:1px solid #e2e8f0;">
    <h2 style="font-size:17px;font-weight:800;color:#0f172a;line-height:1.4;margin:0 0 12px;border-left:4px solid #2563eb;padding-left:14px;">{report.get('headline','')}</h2>
    <p style="font-size:13px;color:#334155;line-height:1.7;margin:0 0 16px;">{report.get('situation_summary','')}</p>
    <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:14px 16px;">
      <div style="font-size:10px;font-weight:700;color:#2563eb;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;">Norway Sector Impact</div>
      <p style="font-size:13px;color:#1e40af;line-height:1.65;margin:0;">{report.get('equinor_impact','')}</p>
    </div>
  </div>

  <div style="padding:20px 32px;display:flex;gap:12px;border-bottom:1px solid #e2e8f0;flex-wrap:wrap;">
    <div style="flex:1;min-width:200px;background:#fef2f2;border-radius:8px;padding:14px 16px;border-top:3px solid #dc2626;">
      <div style="font-size:10px;font-weight:700;color:#dc2626;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;">Top Risk</div>
      <div style="font-size:13px;color:#334155;line-height:1.55;">{report.get('top_risk','')}</div>
    </div>
    <div style="flex:1;min-width:200px;background:#ecfdf5;border-radius:8px;padding:14px 16px;border-top:3px solid #059669;">
      <div style="font-size:10px;font-weight:700;color:#059669;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;">Top Opportunity</div>
      <div style="font-size:13px;color:#334155;line-height:1.55;">{report.get('top_opportunity','')}</div>
    </div>
  </div>

  {'<div style="padding:16px 32px;border-bottom:1px solid #e2e8f0;">' + themes + '</div>' if themes else ''}

  <div style="padding:20px 32px;">
    <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:#64748b;margin-bottom:12px;">High Relevance Articles</div>
    <table style="width:100%;border-collapse:collapse;">{articles_rows}</table>
  </div>

  <div style="background:#f8fafc;padding:16px 32px;border-top:1px solid #e2e8f0;text-align:center;">
    <div style="font-size:11px;color:#94a3b8;">Norwegian Oil Intelligence — Powered by Claude AI + NewsAPI</div>
  </div>
</div>
</body></html>"""


def send_digest(report, email_cfg, alert_messages=None):
    if not email_cfg.get("enabled"):
        return False, "Email digest not enabled"

    to_email   = email_cfg.get("to_email", "").strip()
    smtp_host  = email_cfg.get("smtp_host",  "smtp.gmail.com").strip()
    smtp_port  = int(email_cfg.get("smtp_port", 465))
    smtp_user  = email_cfg.get("smtp_user",  "").strip()
    smtp_pass  = email_cfg.get("smtp_password", "").strip()
    from_email = email_cfg.get("from_email", smtp_user).strip() or smtp_user

    if not all([to_email, smtp_user, smtp_pass]):
        return False, "Incomplete SMTP configuration"

    prefix = "⚠ ALERT" if alert_messages and any(a["level"] == "critical" for a in alert_messages) else "Weekly Brief"
    subject = f"[{prefix}] Norwegian Oil Intelligence — {report.get('date','')}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = from_email
    msg["To"]      = to_email
    msg.attach(MIMEText(_build_html(report, alert_messages), "html"))

    try:
        ctx = ssl.create_default_context()
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx) as s:
                s.login(smtp_user, smtp_pass)
                s.sendmail(from_email, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as s:
                s.ehlo(); s.starttls(context=ctx); s.login(smtp_user, smtp_pass)
                s.sendmail(from_email, [to_email], msg.as_string())
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)
