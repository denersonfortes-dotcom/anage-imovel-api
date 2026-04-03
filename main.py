from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
from bs4 import BeautifulSoup
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/imovel")
async def get_imovel(url: str):
    """Recebe a URL do imovel no site da Anage e retorna dados estruturados."""
    # Remove parametros UTM para URL limpa
    url_limpa = url.split("?")[0]

    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }) as client:
            resp = await client.get(url_limpa)
            resp.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao acessar pagina: {str(e)}")

    soup = BeautifulSoup(resp.text, "html.parser")

    # Titulo
    titulo = ""
    tag_title = soup.find("h1")
    if tag_title:
        titulo = tag_title.get_text(strip=True)

    # Codigo do imovel (pega da URL ou da pagina)
    codigo = ""
    match = re.search(r"-([0-9]+[a-zA-Z])(?:?|$|/)", url_limpa + "?")
    if match:
        codigo = match.group(1).upper()

    # Descricao
    descricao = ""
    # Tenta encontrar o bloco de descricao
    for selector in ["div.property-description", "div.description", "p.description", ".sobre-imovel p", "div[class*='description']", "div[class*='sobre']"]:
        el = soup.select_one(selector)
        if el:
            descricao = el.get_text(separator=" ", strip=True)
            break
    if not descricao:
        # Pega todo o texto da pagina como fallback
        body_text = soup.get_text(separator=" ", strip=True)
        # Procura por padrao de descricao longa
        match_desc = re.search(r"(Casa|Apartamento|Terreno|Sala|Lote|Cobertura).{200,}", body_text)
        if match_desc:
            descricao = match_desc.group(0)[:1500]

    # Fotos - pega URLs do dominio images.anageimoveis.com.br
    fotos = []
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "images.anageimoveis.com.br" in src or "vista.imobi/fotos" in src:
            if src not in fotos:
                fotos.append(src)

    # Tenta tambem em data-src (lazy loading)
    for img in soup.find_all("img"):
        src = img.get("data-src", "")
        if "images.anageimoveis.com.br" in src or "vista.imobi/fotos" in src:
            if src not in fotos:
                fotos.append(src)

    fotos = fotos[:10]

    # Preco
    preco = ""
    price_patterns = [r"R$s*[d.,]+", r"[d]{3}.[d]{3},[d]{2}"]
    page_text = soup.get_text()
    for pattern in price_patterns:
        m = re.search(pattern, page_text)
        if m:
            preco = m.group(0).strip()
            break

    # Bairro e cidade do titulo ou URL
    bairro = ""
    cidade = ""
    url_parts = url_limpa.rstrip("/").split("/")[-1].split("-")
    # Formato tipico: tipo-bairro-cidade-codigo
    if len(url_parts) >= 3:
        cidade = url_parts[-2].replace("-", " ").title() if len(url_parts) > 2 else ""
        bairro_parts = url_parts[1:-2] if len(url_parts) > 3 else url_parts[1:2]
        bairro = " ".join(bairro_parts).title()

    result = {
        "codigo": codigo,
        "titulo": titulo,
        "descricao": descricao,
        "preco": preco,
        "bairro": bairro,
        "cidade": cidade,
        "fotos": fotos,
        "foto_principal": fotos[0] if fotos else "",
        "url": url_limpa
    }

    return result


@app.get("/health")
async def health():
    return {"status": "ok"}
