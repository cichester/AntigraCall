import re
import html

def escape_html(text: str) -> str:
    """Sanitizza i caratteri speciali HTML."""
    return html.escape(text)

def format_blockquote(content: str) -> str:
    """Formatta un blocco citazione in HTML, gestendo gli alert stile GitHub."""
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith('&gt;'):
            stripped = stripped[4:].strip()
        lines.append(stripped)
    
    header = ""
    if lines:
        first_line = lines[0]
        alert_match = re.match(r'^\[!(TIP|NOTE|IMPORTANT|WARNING|CAUTION)\]', first_line, re.IGNORECASE)
        if alert_match:
            alert_type = alert_match.group(1).upper()
            emoji_map = {
                "TIP": "💡 TIP",
                "NOTE": "ℹ️ NOTA",
                "IMPORTANT": "❗ IMPORTANTE",
                "WARNING": "⚠️ ATTENZIONE",
                "CAUTION": "🛑 ATTENZIONE"
            }
            emoji = emoji_map.get(alert_type, alert_type)
            header = f"<b>{emoji}</b>\n"
            lines = lines[1:]

    inner_text = "\n".join(lines).strip()
    return f"<blockquote>{header}{inner_text}</blockquote>\n"


def markdown_to_html(text: str) -> str:
    """
    Converte un testo in Markdown in HTML compatibile con Telegram.
    Isola blocchi di codice, codice inline e link, quindi sanitizza ed applica il markup.
    """
    if not text:
        return ""

    # 1. Riconosciamo ed escludiamo i blocchi di codice fenzati (```lang ... ```)
    code_blocks = []
    def save_code_block(match):
        lang = match.group(1) or ""
        code = match.group(2)
        # Il codice interno va sanitizzato ma non formattato
        escaped_code = html.escape(code)
        code_blocks.append(f'<pre><code class="language-{lang}">{escaped_code}</code></pre>')
        return f"CODEBLOCK{len(code_blocks)-1}BLOCK"

    text = re.sub(r'```(\w*)\n(.*?)\n```', save_code_block, text, flags=re.DOTALL)

    # 2. Riconosciamo ed escludiamo il codice inline (`code`)
    inline_codes = []
    def save_inline_code(match):
        code = match.group(1)
        escaped_code = html.escape(code)
        inline_codes.append(f"<code>{escaped_code}</code>")
        return f"INLINECODE{len(inline_codes)-1}CODE"

    text = re.sub(r'`(.*?)`', save_inline_code, text)

    # 3. Sostituiamo gli asterischi e i trattini delle liste con bullet point standard
    # per evitare falsi positivi nel corsivo
    text = re.sub(r'^\s*[\*\-]\s+', '• ', text, flags=re.MULTILINE)

    # 4. Estraiamo gli URL dei link per evitare che vengano formattati (es. se contengono underscore)
    urls = []
    def save_url(match):
        label = match.group(1)
        url = match.group(2)
        urls.append(url)
        return f"[{label}](URLPLACEHOLDER{len(urls)-1}PLACEHOLDER)"

    text = re.sub(r'\[(.*?)\]\((.*?)\)', save_url, text)

    # 5. Sanitizziamo tutto il resto del testo (che ora non contiene tag HTML o URL con caratteri speciali)
    text = html.escape(text)

    # 6. Gestione Intestazioni (Headers # -> Bold)
    text = re.sub(r'^#{1,6}\s+(.*?)$', r'<b>\1</b>', text, flags=re.MULTILINE)

    # 7. Gestione Blockquote e GitHub Alerts (cercando '&gt;' dopo l'escaping)
    def repl_blockquote(match):
        return format_blockquote(match.group(0))
        
    text = re.sub(r'(?:^\s*&gt;.*(?:\n|$))+', repl_blockquote, text, flags=re.MULTILINE)

    # 8. Convertiamo il grassetto-corsivo (triple asterschi/underscore)
    text = re.sub(r'(?<!\w)\*\*\*(?!\s)(.*?)(?<!\s)\*\*\*(?!\w)', r'<b><i>\1</i></b>', text)
    text = re.sub(r'(?<!\w)___(?!\s)(.*?)(?<!\s)___(?!\w)', r'<b><i>\1</i></b>', text)

    # 9. Convertiamo il grassetto **testo** o __testo__
    text = re.sub(r'(?<!\w)\*\*(?!\s)(.*?)(?<!\s)\*\*(?!\w)', r'<b>\1</b>', text)
    text = re.sub(r'(?<!\w)__(?!\s)(.*?)(?<!\s)__(?!\w)', r'<b>\1</b>', text)

    # 10. Convertiamo il corsivo *testo* o _testo_
    text = re.sub(r'(?<!\w)\*(?!\s)(.*?)(?<!\s)\*(?!\w)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!\w)_(?!\s)(.*?)(?<!\s)_(?!\w)', r'<i>\1</i>', text)

    # 11. Ripristiniamo i link convertendoli in tag HTML <a>
    def restore_link(match):
        label = match.group(1)
        url_idx = int(match.group(2))
        url = urls[url_idx]
        # Ripristiniamo l'escape solo dall'URL per non rompere il link HTML
        url_unescaped = html.unescape(url)
        return f'<a href="{url_unescaped}">{label}</a>'

    text = re.sub(r'\[(.*?)\]\(URLPLACEHOLDER(\d+)PLACEHOLDER\)', restore_link, text)

    # 12. Ripristiniamo i blocchi di codice e il codice inline
    for i, block in enumerate(code_blocks):
        text = text.replace(f"CODEBLOCK{i}BLOCK", block)

    for i, inline in enumerate(inline_codes):
        text = text.replace(f"INLINECODE{i}CODE", inline)

    return text
