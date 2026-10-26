from io import BytesIO
import pandas as pd
from .refining import crack_series

def safe_cell(value):
    # Prevent formula injection from untrusted RSS strings in Excel.
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value

def excel_bytes(news, prices, runs):
    output = BytesIO()
    cracks = pd.concat([crack_series(prices, code) for code in ("DCOILWTICO", "DCOILBRENTEU")], ignore_index=True)
    if not cracks.empty:
        cracks["date"] = cracks.date.dt.strftime("%Y-%m-%d")
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, frame in [("News", news), ("Prices", prices), ("Collection status", runs), ("Crack spreads", cracks)]:
            safe = frame.map(safe_cell)
            safe.to_excel(writer, sheet_name=name, index=False)
            sheet = writer.sheets[name]
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            for column in sheet.columns:
                sheet.column_dimensions[column[0].column_letter].width = min(65, max(15, max(len(str(c.value or "")) for c in column[:100]) + 2))
        pd.DataFrame({"Note": ["News filters apply to News only. Prices and collection status are full snapshots.",
            "Signals are keyword mentions, not forecasts. Dates are UTC; missing publication dates remain blank.",
            "EIA via FRED: DCOILBRENTEU/DCOILWTICO USD/barrel; DGASNYH/DHOILNYH/DDFUELUSGULF USD/gallon. Spot, not futures.",
            "News text is limited to RSS/NewsAPI metadata. Publisher rights remain with publishers.",
            "Cracks: 42*product-crude; 3:2:1 = 42*(2*gasoline+ULSD)/3-crude. Products US Gulf Coast, crude WTI or Brent, USD/bbl; matched dates only. Not net refinery margin.",
            "DGASUSGULF: conventional gasoline, not RBOB. No costs, quality or location adjustments included."]}).to_excel(writer, sheet_name="Read me", index=False)
    return output.getvalue()
