import sys
import logging
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QListWidget, QInputDialog
)
from odoo.connect_odoo import conectar_con_reintentos
from odoo.orders_service_odoo import (
    confirm_sales_order,
    cargar_producto_a_orden_de_venta
)
from odoo.clients_service_odoo import get_client_id_by_dni

# Función para crear la orden de venta desde AppVentas
def create_sales_order(client_id, date, models, db, uid, password, order_number=None):
    if not all([models, db, uid, password]):
        logging.error("❌ No se pudo establecer conexión con Odoo para crear orden.")
        return None

    try:
        client_order_ref = f"AppVentas - #{order_number}" if order_number else "AppVentas"
        order_id = models.execute_kw(
            db, uid, password,
            "sale.order", "create",
            [{
                "partner_id": client_id,
                "date_order": date,
                "client_order_ref": client_order_ref
            }]
        )
        return order_id

    except Exception as e:
        logging.exception(f"💥 Error creando orden de venta: {str(e)}")
        return None

# Función para obtener productos masivamente SIN stock
def get_all_products(models, db, uid, password):
    try:
        productos = models.execute_kw(
            db, uid, password,
            'product.template', 'search_read',
            [[]],
            {'fields': [
                'name', 'default_code', 'list_price',
                'x_studio_propiedad_1', 'x_studio_propiedad_2', 'x_studio_propiedad_3'
            ]}
        )
        return productos
    except Exception as e:
        logging.exception(f"💥 Error al obtener productos: {str(e)}")
        return []

# Función para obtener stock actualizado de un producto puntual
def get_stock(models, db, uid, password, product_id):
    try:
        result = models.execute_kw(
            db, uid, password,
            'product.template', 'read',
            [product_id],
            {'fields': ['virtual_available']}
        )
        if result and isinstance(result, list):
            return result[0].get('virtual_available', 0)
        return 0
    except Exception as e:
        logging.exception(f"💥 Error al obtener stock: {str(e)}")
        return 0

class VentanaVentas(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestión de Ventas - Odoo")
        self.resize(1200, 600)

        # Layout principal
        layout = QHBoxLayout()

        # --- Panel izquierdo: búsqueda y resultados ---
        panel_izq = QVBoxLayout()

        boton_nueva_venta = QPushButton("Nueva venta")
        boton_nueva_venta.clicked.connect(self.nueva_venta)
        panel_izq.addWidget(boton_nueva_venta)

        self.busqueda = QLineEdit()
        self.busqueda.setPlaceholderText("Buscar por nombre, SKU o propiedades...")
        panel_izq.addWidget(self.busqueda)

        boton_buscar = QPushButton("Buscar")
        boton_buscar.clicked.connect(self.buscar_productos)
        panel_izq.addWidget(boton_buscar)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(6)
        self.tabla.setHorizontalHeaderLabels([
            "Nombre", "SKU", "Precio",
            "Propiedad1", "Propiedad2", "Propiedad3"
        ])
        panel_izq.addWidget(self.tabla)

        boton_agregar = QPushButton("Agregar a orden")
        boton_agregar.clicked.connect(self.agregar_a_orden)
        panel_izq.addWidget(boton_agregar)

        layout.addLayout(panel_izq)

        # --- Panel derecho: orden en construcción ---
        panel_der = QVBoxLayout()
        self.lista_orden = QListWidget()
        panel_der.addWidget(self.lista_orden)

        boton_confirmar = QPushButton("Confirmar orden")
        boton_confirmar.clicked.connect(self.confirmar_orden)
        panel_der.addWidget(boton_confirmar)
        boton_eliminar = QPushButton("Eliminar producto seleccionado")
        boton_eliminar.clicked.connect(self.eliminar_producto)
        panel_der.addWidget(boton_eliminar)

        layout.addLayout(panel_der)

        self.setLayout(layout)

        # Conexión a Odoo
        self.models, self.db, self.uid, self.password = conectar_con_reintentos()

        # Carga inicial de productos (sin stock)
        self.productos = get_all_products(self.models, self.db, self.uid, self.password)
        self.orden = []

    def nueva_venta(self):
        if self.orden:
            respuesta = QMessageBox.question(
                self,
                "Confirmar",
                "¿Seguro que querés borrar la orden actual?",
                QMessageBox.Yes | QMessageBox.No
            )
            if respuesta == QMessageBox.No:
                return

        self.orden.clear()
        self.lista_orden.clear()
        QMessageBox.information(self, "Nueva venta", "Orden borrada. Podés iniciar una nueva venta.")

    def eliminar_producto(self):
        fila = self.lista_orden.currentRow()
        if fila < 0:
            QMessageBox.warning(self, "Error", "Seleccioná un producto de la orden para eliminar.")
            return

        eliminado = self.orden.pop(fila)
        self.lista_orden.takeItem(fila)
        QMessageBox.information(self, "Producto eliminado", f"Se eliminó {eliminado['name']} de la orden.")

    def buscar_productos(self):
        criterio = self.busqueda.text().lower()
        resultados = []

        for p in self.productos:
            nombre = str(p.get("name") or "").lower()
            sku = str(p.get("default_code") or "").lower()
            prop1 = str(p.get("x_studio_propiedad_1") or "").lower()
            prop2 = str(p.get("x_studio_propiedad_2") or "").lower()
            prop3 = str(p.get("x_studio_propiedad_3") or "").lower()

            if (criterio in nombre or criterio in sku or
                criterio in prop1 or criterio in prop2 or criterio in prop3):
                resultados.append(p)

        self.tabla.setRowCount(len(resultados))
        for fila, prod in enumerate(resultados):
            self.tabla.setItem(fila, 0, QTableWidgetItem(str(prod.get("name", ""))))
            self.tabla.setItem(fila, 1, QTableWidgetItem(str(prod.get("default_code", ""))))
            self.tabla.setItem(fila, 2, QTableWidgetItem(str(prod.get("list_price", 0))))
            self.tabla.setItem(fila, 3, QTableWidgetItem(str(prod.get("x_studio_propiedad_1", ""))))
            self.tabla.setItem(fila, 4, QTableWidgetItem(str(prod.get("x_studio_propiedad_2", ""))))
            self.tabla.setItem(fila, 5, QTableWidgetItem(str(prod.get("x_studio_propiedad_3", ""))))

    def agregar_a_orden(self):
        fila = self.tabla.currentRow()
        if fila < 0:
            QMessageBox.warning(self, "Error", "Seleccioná un producto primero.")
            return

        nombre = self.tabla.item(fila, 0).text()
        sku = self.tabla.item(fila, 1).text()
        precio = float(self.tabla.item(fila, 2).text())

        cantidad, ok = QInputDialog.getInt(self, "Cantidad", f"Ingresá cantidad para {nombre}:", 1, 1)
        if not ok:
            return

        self.orden.append({"name": nombre, "sku": sku, "cantidad": cantidad, "precio": precio})
        self.lista_orden.addItem(f"{nombre} (SKU: {sku}) x {cantidad}")

    def confirmar_orden(self):
        if not self.orden:
            QMessageBox.warning(self, "Error", "La orden está vacía.")
            return

        try:
            # Validación de stock antes de confirmar
            for producto in self.orden:
                # Buscar el product.template correspondiente
                prod_match = next((p for p in self.productos if p.get("default_code") == producto["sku"]), None)
                if not prod_match:
                    QMessageBox.warning(self, "Error", f"No se encontró el producto {producto['name']} en catálogo.")
                    return

                product_id = prod_match["id"]
                stock_actual = get_stock(self.models, self.db, self.uid, self.password, product_id)

                if producto["cantidad"] > stock_actual:
                    QMessageBox.warning(self, "Stock insuficiente",
                                        f"El producto {producto['name']} tiene solo {stock_actual} unidades disponibles.")
                    return

            # Cliente ficticio: en producción deberías pedir DNI/nombre/email
            client_id_odoo = get_client_id_by_dni("00000000", "Cliente Genérico", "cliente@example.com",
                                                  self.models, self.db, self.uid, self.password)

            date = datetime.now()
            order_sale_id_odoo = create_sales_order(client_id_odoo, date,
                                                    self.models, self.db, self.uid, self.password,
                                                    order_number="VENTA_APP")

            for producto in self.orden:
                cargar_producto_a_orden_de_venta(order_sale_id_odoo,
                                                producto["sku"],
                                                producto["cantidad"],
                                                producto["precio"],
                                                self.models, self.db, self.uid, self.password)

            confirm_sales_order(order_sale_id_odoo, self.models, self.db, self.uid, self.password)

            QMessageBox.information(self, "Orden confirmada",
                                    f"La orden fue creada exitosamente en Odoo (ID: {order_sale_id_odoo}).")

            self.orden.clear()
            self.lista_orden.clear()

        except Exception as e:
            logging.exception(f"💥 Error creando orden en Odoo: {str(e)}")
            QMessageBox.critical(self, "Error", f"No se pudo crear la orden: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = VentanaVentas()
    ventana.show()
    sys.exit(app.exec_())
