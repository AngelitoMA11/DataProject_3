import requests
from IPython.display import display, HTML
import ipywidgets as widgets

def buscar_alojamientos(api_key_serpapi, ciudad, fecha_inicio, fecha_fin, adultos):
    params = {
        "engine": "google_hotels",
        "q": f"hoteles en {ciudad}",
        "check_in_date": fecha_inicio,
        "check_out_date": fecha_fin,
        "adults": adultos,
        "currency": "EUR",
        "gl": "es",
        "hl": "es",
        "api_key": api_key_serpapi
    }

    response = requests.get("https://serpapi.com/search", params=params)
    if response.status_code != 200:
        print("❌ Error al obtener los resultados.")
        return []

    data = response.json()
    alojamientos = data.get("properties", [])

    if not alojamientos:
        print("⚠️ No se encontraron alojamientos.")
        return []

    resultados = []
    for alojamiento in alojamientos:
        nombre = alojamiento.get("name", "Sin nombre")
        precio = alojamiento.get("rate_per_night", {}).get("lowest", "No disponible")
        rating = alojamiento.get("overall_rating", "No disponible")
        opiniones = alojamiento.get("reviews", 0)
        categoria = alojamiento.get("hotel_class", "Sin categoría")
        coordenadas = alojamiento.get("gps_coordinates", {})
        lat = coordenadas.get("latitude")
        lon = coordenadas.get("longitude")
        mapa_url = f"https://www.google.com/maps?q={lat},{lon}" if lat and lon else "Ubicación no disponible"
        imagenes = [img.get("thumbnail") for img in alojamiento.get("images", []) if img.get("thumbnail")]
        imagenes = list(filter(None, imagenes))[:5]
        enlace_info = alojamiento.get("url") or alojamiento.get("booking_url") or "No disponible"

        resultados.append({
            "nombre": nombre,
            "precio": precio,
            "rating": rating,
            "opiniones": opiniones,
            "categoria": categoria,
            "imagenes": imagenes,
            "mapa_url": mapa_url,
            "enlace_info": enlace_info
        })

    # Mostrar resultados
    for i, hotel in enumerate(resultados):
        print(f"\n[{i}] 🏨 {hotel['nombre']}")
        print(f"   💶 Precio: {hotel['precio']} por noche")
        print(f"   ⭐ Rating: {hotel['rating']} ({hotel['opiniones']} opiniones)")
        print(f"   🏷️ Categoría: {hotel['categoria']}")
        print(f"   🌍 Ver en Google Maps: {hotel['mapa_url']}")
        print(f"   🔗 Más información: {hotel['enlace_info']}")

        # Imagen destacada
        if hotel['imagenes']:
            display(HTML(f'<img src="{hotel["imagenes"][0]}" width="250" style="margin:5px; border-radius:10px;"/>'))

        out = widgets.Output()
        boton = widgets.Button(
            description="📸 Ver más fotos",
            button_style='info',
            tooltip=f"Ver fotos de {hotel['nombre']}"
        )

        # Estado del botón para toggle
        def make_handler(hotel_data, output_widget, boton_widget):
            mostrado = {"visible": False}
            def handler(b):
                output_widget.clear_output()
                if not mostrado["visible"]:
                    with output_widget:
                        print(f"📸 Más fotos de: {hotel_data['nombre']}")
                        for url in hotel_data['imagenes']:
                            display(HTML(f'<img src="{url}" width="300" style="margin:5px; border-radius:10px;"/>'))
                    boton_widget.description = "🔙 Ocultar fotos"
                else:
                    boton_widget.description = "📸 Ver más fotos"
                mostrado["visible"] = not mostrado["visible"]
            return handler

        boton.on_click(make_handler(hotel, out, boton))
        display(boton, out)

    return resultados

def elegir_alojamiento(opciones_alojamiento):
    print("\n🏨 Alojamientos disponibles:")
    for idx, hotel in enumerate(opciones_alojamiento):
        nombre = hotel.get("nombre", "Sin nombre")
        precio = hotel.get("precio", "N/A")
        rating = hotel.get("rating", "Sin rating")
        print(f"[{idx}] 🏨 {nombre} - {precio}/noche - {rating}★")

    while True:
        try:
            eleccion = int(input("\n✋ Elige el número del alojamiento que prefieras: "))
            if 0 <= eleccion < len(opciones_alojamiento):
                hotel_elegido = opciones_alojamiento[eleccion]
                print(f"\n✅ Alojamiento elegido: {hotel_elegido['nombre']} - {hotel_elegido['precio']}/noche")
                mostrar_detalles(hotel_elegido)
                return hotel_elegido
            else:
                print("❌ Número inválido. Intenta de nuevo.")
        except ValueError:
            print("❌ Entrada no válida. Escribe un número.")

def mostrar_detalles(hotel):
    print("\n✨ Detalles del alojamiento seleccionado:")
    print(f"🏨 {hotel['nombre']}")
    print(f"💶 Precio por noche: {hotel['precio']}")
    print(f"⭐ Rating: {hotel['rating']}")
    print(f"🏷️ Categoría: {hotel['categoria']}")
    print(f"🌍 Ubicación: {hotel['mapa_url']}")
    print(f"🔗 Enlace a la reserva: {hotel['enlace_info']}")
    print("\n🖼️ Imágenes del alojamiento:")
    for img_url in hotel['imagenes']:
        display(HTML(f'<img src="{img_url}" width="300" style="margin:5px; border-radius:10px;"/>'))
