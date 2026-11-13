from playwright.sync_api import sync_playwright


def iniciar_sesion(usuario: str, password: str):
  print("1 - iniciando Playwright")

  with sync_playwright() as p:
    print("2 - lanzando navegador")

    browser = p.chromium.launch(
      headless=False
    )

    print("3 - creando página")

    page = browser.new_page()

    print("4 - navegando")

    page.goto(
      "https://account.sovos.com/es-ES"
    )

    print("5 - página cargada:", page.url)

    page.get_by_label("Correo electrónico").fill(usuario)

    print("6 - usuario ingresado")

    page.get_by_label("Contraseña").fill(password)

    print("7 - contraseña ingresada")

    page.get_by_role(
      "button",
      name="Iniciar sesión"
    ).click()

    print("8 - botón presionado")

    page.wait_for_load_state("networkidle")

    print("9 - login terminado")
    print("URL:", page.url)

    


iniciar_sesion(
  "dquioza@smu.cl",
  "Unhamster123!"
)