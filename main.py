from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ANAGE_API = "https://api.anageimoveis.com.br/api/router?url={slug}"


@app.get("/imovel")
async def get_imovel(url: str):
    # Extrai o slug da URL (ex: casa-vila-nova-joinville-29415n)
    url_limpa = url.split("?")[0].rstrip("/")
    slug = url_limpa.split("/")[-1]

    api_url = ANAGE_API.format(slug=slug)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(api_url)
            resp.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao acessar API Anage: {str(e)}")

    try:
        data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao parsear JSON: {str(e)}")

    if not data.get("success"):
        raise HTTPException(status_code=404, detail="Imovel nao encontrado")

    imovel = data["content"]["content"]

    # Fotos da galeria
    gallery = imovel.get("gallery", [])
    fotos = [g["image"] for g in gallery if g.get("image")][:10]
    foto_principal = fotos[0] if fotos else ""

    # Preco formatado
    preco_raw = imovel.get("price", "0")
    try:
        preco = f"R$ {float(preco_raw):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        preco = str(preco_raw)

    return {
        "codigo": imovel.get("code", ""),
        "titulo": imovel.get("name", ""),
        "descricao": imovel.get("description", ""),
        "preco": preco,
        "quartos": imovel.get("bedrooms", ""),
        "suites": imovel.get("suites", ""),
        "banheiros": imovel.get("toilets", ""),
        "garagem": imovel.get("parkingSpaces", ""),
        "area_construida": imovel.get("constructedArea", ""),
        "area_terreno": imovel.get("landArea", ""),
        "bairro": imovel.get("neighbourhood", ""),
        "cidade": imovel.get("city", ""),
        "estado": imovel.get("state", ""),
        "endereco": imovel.get("address", ""),
        "tipo": imovel.get("category", {}).get("name", ""),
        "fotos": fotos,
        "foto_principal": foto_principal,
        "url": url_limpa
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
