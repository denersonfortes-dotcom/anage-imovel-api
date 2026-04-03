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
    tag_h1 = soup.find("h1")
    if tag_h1:
        titulo = tag_h1.get_text(strip=True)

    # Codigo da URL
    codigo = ""
    match = re.search(r"-([0-9a-zA-Z]{5,7}n)(?:\?|$)", url_limpa, re.IGNORECASE)
    if match:
        codigo = match.group(1).upper()

    # Descricao - pega todo o texto da pagina e extrai parte relevante
    page_text = soup.get_text(separator=" ", strip=True)
    descricao = ""
    match_desc = re.search(r"(Casa|Apartamento|Terreno|Sala|Lote|Cobertura|Imóvel).{100,1500}", page_text)
    if match_desc:
        descricao = match_desc.group(0)

    # Fotos
    fotos = []
    for img in soup.find_all("img"):
        for attr in ["src", "data-src", "data-lazy-src"]:
            src = img.get(attr, "")
            if ("images.anageimoveis.com.br" in src or "vista.imobi/fotos" in src) and src not in fotos:
                fotos.append(src)

    fotos = fotos[:10]

    # Preco
    preco = ""
    m = re.search(r"R\$\s*[d.,]+", page_text)
    if m:
        preco = m.group(0).strip()

    # Bairro e cidade da URL
    slug = url_limpa.rstrip("/").split("/")[-1]
    parts = slug.split("-")
    bairro = ""
    cidade = ""
    if len(parts) >= 4:
        cidade = parts[-2].title()
        bairro = " ".join(parts[1:-2]).title()

    return {
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


@app.get("/health")
async def health():
    return {"status": "ok"}
