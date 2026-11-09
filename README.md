# Simulación de un CDA (Centro de Diagnóstico Automotor)

Aplicación en Streamlit que simula una jornada de trabajo en un CDA con llegadas aleatorias de vehículos, tres pistas de inspección, inspectores con nombre, contratiempos y calificación de satisfacción de los clientes.

## Qué hace
- Genera vehículos (motos, livianos y pesados) que llegan a horas aleatorias, hasta la hora de cierre.
- Los vehículos que ya están en fila al cierre se siguen atendiendo hasta que salga el último.
- Horario de apertura y cierre, días laborales y festivos configurables.
- Cada vehículo pasa por 3 estaciones, con tiempo medido en cada una y un inspector asignado.
- Tiempos promedio: motos 35–45 min; livianos y pesados 45–60 min. Algunos vehículos tienen contratiempos que alargan la revisión.
- Al salir, cada cliente califica la atención de 0 a 5 estrellas según la espera y las demoras.
- Gráficas, tabla de registro y exportación a CSV y Excel.

## Cómo ejecutarla
```
pip install -r requirements.txt
python -m streamlit run app_cda_v2.py
```
Se abre en el navegador en `http://localhost:8501`.

## Cómo usarla
1. Configura el día, el horario, el personal y la cantidad de vehículos en la barra lateral.
2. Pulsa **Generar jornada**.
3. Pulsa **Iniciar** para que corra el reloj.
4. Revisa las pestañas Mapa de Pistas, Analytics y Satisfacción, y descarga los datos desde Registro y Exportación.
