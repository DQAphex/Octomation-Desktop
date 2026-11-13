def remove_symbol(val:str):
  symbols = [">","<"]
  hasSymbols = any(c in val for c in symbols)
  if hasSymbols:
    for s in symbols:
      if s in val:
        newVal = val.replace(s,"")
    return newVal
  return val
def replace_thousands_separator(value):
  if "." in value:
    return value.replace(".",",")
  else:
    return value
def remove_units(value):
  invalidCharacters = "mg/LlH"
  newvalue = ""
  for i in range(len(value)):
    if value[i] not in invalidCharacters:
      newvalue += value[i]
  return newvalue
def full_parsing(value):
  valueWithOutSymbols = remove_symbol(value)
  valueCommaTS = replace_thousands_separator(valueWithOutSymbols)
  finalValue = remove_units(valueCommaTS)
  return finalValue

    