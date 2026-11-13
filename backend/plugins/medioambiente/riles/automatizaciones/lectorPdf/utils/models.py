import pandas as pd
from thefuzz import process, fuzz
from lector_pdf_config import LOCALES_CSV

def search_store_id(direccion_ingresada, limite_confianza=60):

    dataframe = pd.read_csv(LOCALES_CSV,sep=';')
    
    resultado = process.extractOne(
        direccion_ingresada, 
        dataframe['DIRECCIÓN'], 
        scorer=fuzz.token_sort_ratio
    )
    
    if not resultado:
        return "No se encontraron coincidencias."
        
    mejor_coincidencia, score, indice = resultado

    if score >= limite_confianza:
        local_id = dataframe.loc[indice, 'ID_LOCAL']
        local_region = dataframe.loc[indice, 'REGIÓN']
        local_comuna = dataframe.loc[indice, 'COMUNA']
        local_nombre = dataframe.loc[indice, 'LOCAL']
        local_rpm = int(dataframe.loc[indice, 'RPM'])
        empresa = dataframe.loc[indice, 'EMPRESA DISTRIBUIDORA']
        estado_local = dataframe.loc[indice, 'ESTADO']
        local_convenio = dataframe.loc[indice, 'CONVENIO']
        formato_local = dataframe.loc[indice, 'FORMATO']

        return {
            'similitud': score,
            'local_id': local_id,
            'local_nombre':local_nombre,
            'local_comuna':local_comuna,
            'local_region':local_region,
            'local_direccion': mejor_coincidencia,
            'local_rpm':local_rpm,
            'empresa':empresa,
            'estado_local':estado_local,
            'local_convenio':local_convenio,
            'formato_local':formato_local
        }
    else:
        return f"{direccion_ingresada} | {score}%"


# usuario_input = "Nicaragua"
# resultado_busqueda = search_store_id(usuario_input)

# print(resultado_busqueda)