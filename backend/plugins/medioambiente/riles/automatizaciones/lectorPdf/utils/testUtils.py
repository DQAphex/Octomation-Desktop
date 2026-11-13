import json

labKeywordJsonPath = "labKeywords.json"

def a(lab):
    # Usamos 'utf-8-sig' para evitar errores por caracteres ocultos (BOM)
    with open(labKeywordJsonPath, "r", encoding="utf-8-sig") as keywordsJson:
        keyWordsData = json.load(keywordsJson)
        return keyWordsData[lab]['tabla']

print(a("biodiversa"))