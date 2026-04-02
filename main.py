from fastapi import FastAPI, HTTPException
import httpx
import xml.etree.ElementTree as ET
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

XML_URL = "https://anageimo-portais.vistahost.com.br/4f13834f2cdbf7b3bd53c37f67de7b43"
NS = {"vr": "http://www.vivareal.com/schemas/1.0/VRSync"}

@app.get("/imovel")
async def get_imovel(codigo: str):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(XML_URL)
            resp.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao buscar XML: {str(e)}")

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        raise HTTPException(status_code=500, detail=f"Erro ao parsear XML: {str(e)}")

    listing = None
    for l in root.findall(".//vr:Listing", NS):
        lid = l.find("vr:ListingID", NS)
        if lid is not None and lid.text == codigo:
            listing = l
            break

    if listing is None:
        raise HTTPException(status_code=404, detail=f"Imovel {codigo} nao encontrado")

    def txt(el, tag):
        node = el.find(tag, NS)
        return node.text.strip() if node is not None and node.text else ""

    details = listing.find("vr:Details", NS) or ET.Element("Details")
    location = listing.find("vr:Location", NS) or ET.Element("Location")

    fotos = []
    media = listing.find("vr:Media", NS)
    if media is not None:
        for item in media.findall("vr:Item", NS):
            if item.get("medium") == "image" and item.text:
                fotos.append(item.text.strip())

    preco_node = details.find("vr:ListPrice", NS)
    preco = preco_node.text.strip() if preco_node is not None and preco_node.text else "0"

    features = []
    feats = details.find("vr:Features", NS)
    if feats is not None:
        for f in feats.findall("vr:Feature", NS):
            if f.text:
                features.append(f.text.strip())

    result = {
        "codigo": txt(listing, "vr:ListingID"),
        "tipo": txt(details, "vr:PropertyType"),
        "descricao": txt(details, "vr:Description"),
        "titulo": txt(listing, "vr:Title"),
        "quartos": txt(details, "vr:Bedrooms"),
        "banheiros": txt(details, "vr:Bathrooms"),
        "suites": txt(details, "vr:Suites"),
        "garagem": txt(details, "vr:Garage"),
        "area_construida": txt(details, "vr:LivingArea"),
        "area_terreno": txt(details, "vr:LotArea"),
        "preco": preco,
        "ano": txt(details, "vr:YearBuilt"),
        "bairro": txt(location, "vr:Neighborhood"),
        "cidade": txt(location, "vr:City"),
        "estado": txt(location, "vr:State"),
        "endereco": txt(location, "vr:Address"),
        "diferenciais": features,
        "fotos": fotos[:10],
        "foto_principal": fotos[0] if fotos else ""
    }

    return result


@app.get("/health")
async def health():
    return {"status": "ok"}
