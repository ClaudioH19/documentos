import json
import folium
from folium import Circle, Marker


def load_estaciones(path='estaciones.json'):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('estaciones', [])


def crear_mapa(estaciones, centro=None, radio_m=100, output='map.html'):
    # Si no se entrega centro, usar Talca si existe, sino la primera estación
    if centro is None:
        talca = next((e for e in estaciones if e.get('comuna', '').lower().startswith('talca')), None)
        if talca:
            centro = (talca['latitud'], talca['longitud'])
        elif estaciones:
            centro = (estaciones[0]['latitud'], estaciones[0]['longitud'])
        else:
            centro = (-35.5, -71.6)  # fallback

    m = folium.Map(location=centro, zoom_start=9, tiles='OpenStreetMap')

    # Añadir marcadores
    for est in estaciones:
        lat = est.get('latitud')
        lon = est.get('longitud')
        name = est.get('comuna') or str(est.get('codigo_estacion', ''))
        popup = folium.Popup(f"{name}<br>alt={est.get('altura')}, code={est.get('codigo_estacion')}", max_width=300)
        Marker(location=(lat, lon), popup=popup).add_to(m)
        Circle(location=(lat, lon), radius=radio_m, color='red', fill=True, fill_opacity=0.1, popup=f"{radio_m/1000} km radio").add_to(m)


    # Guarda el mapa
    m.save(output)
    print(f'Mapa guardado en {output}')


if __name__ == '__main__':
    estaciones = load_estaciones('estaciones.json')
    # Centro por defecto: Talca
    talca = next((e for e in estaciones if e.get('comuna', '').lower().startswith('talca')), None)
    crear_mapa(estaciones, radio_m=100, output='map.html')
