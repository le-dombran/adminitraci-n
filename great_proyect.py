import streamlit as st
import sqlite3
import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Sistema de Gestión Comercial", page_icon="💼", layout="wide")

# --- CONEXIÓN Y CREACIÓN DE TABLAS (SQLITE) ---
def inicializar_bd():
    conn = sqlite3.connect("Inventario.db")
    cursor = conn.cursor()
    
    # 1. Tabla de Usuarios/Empresas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        nombre_empresa TEXT,
        estado TEXT DEFAULT 'Activo',
        proximo_pago DATE
    )
    """)
    
    # 2. Tabla de Productos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa TEXT,
        nombre_producto TEXT,
        precio REAL,
        cantidad INTEGER
    )
    """)
    
    # 3. Tabla de Ventas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa TEXT,
        producto TEXT,
        cantidad INTEGER,
        total REAL,
        fecha DATE,
        caja_cerrada INTEGER DEFAULT 0
    )
    """)
    
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO usuarios (username, password, nombre_empresa, estado, proximo_pago) VALUES (?, ?, ?, ?, ?)",
            ("Brandon", "Brandon0730*", "Brandon Admin", "Activo", "2030-12-31")
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
        
    conn.close()

inicializar_bd()

# --- FUNCIONES DE BASE DE DATOS ---
def eliminar_negocio_db(id_cliente):
    conn = sqlite3.connect("Inventario.db")
    cursor = conn.cursor()
    try:
        fecha_borrado = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{fecha_borrado}] ELIMINACIÓN PERMANENTE: ID Cliente {id_cliente}")
        cursor.execute("DELETE FROM usuarios WHERE id = ?", (id_cliente,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al eliminar: {e}")
        return False
    finally:
        conn.close()

def login_user(user, pwd):
    conn = sqlite3.connect("Inventario.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username, nombre_empresa, estado, proximo_pago FROM usuarios WHERE username = ? AND password = ?", (user, pwd))
    result = cursor.fetchone()
    conn.close()
    return result

def verificar_password_usuario(username, pwd_a_verificar):
    conn = sqlite3.connect("Inventario.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE username = ? AND password = ?", (username, pwd_a_verificar))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# --- MANEJO DE SESIÓN EN STREAMLIT ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.perfil = ""
    st.session_state.empresa = ""

# --- INTERFAZ DE LOG IN ---
if not st.session_state.logged_in:
    st.title("🔑 Sistema de Gestión - Iniciar Sesión")
    
    with st.form("login_form"):
        usuario_input = st.text_input("Usuario (Empresa)")
        clave_input = st.text_input("Contraseña", type="password")
        boton_entrar = st.form_submit_button("Ingresar al Sistema")
        
        if boton_entrar:
            user_data = login_user(usuario_input, clave_input)
            if user_data:
                username, nombre_empresa, estado, proximo_pago = user_data
                hoy = datetime.date.today().strftime("%Y-%m-%d")
                
                if username != "Brandon" and (estado == "Suspendido" or proximo_pago < hoy):
                    st.error("❌ **Servicio Interrumpido.** Tu suscripción ha vencido o está suspendida. Contacta a Brandon para activar el servicio.")
                else:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.empresa = nombre_empresa
                    st.session_state.perfil = "admin" if username == "Brandon" else "cliente"
                    st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

# --- INTERFAZ DEL PROGRAMA AUTENTICADO ---
else:
    st.sidebar.title(f"🏢 {st.session_state.empresa}")
    st.sidebar.caption(f"👤 Usuario: {st.session_state.username}")
    
    def cerrar_sesion():
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.perfil = ""
        st.session_state.empresa = ""
        st.rerun()

    # ==========================================
    # 👑 PERFIL DE ADMINISTRADOR (BRANDON)
    # ==========================================
    if st.session_state.perfil == "admin":
        st.sidebar.button("🚪 Cerrar Sesión", on_click=cerrar_sesion)
        st.title("👑 Panel de Control Supremo - Brandon Admin")
        
        tab1, tab2 = st.tabs(["📊 Monitorear y Modificar Clientes", "➕ Registrar Nueva Empresa"])
        
        with tab1:
            st.subheader("Estado de Clientes y Suscripciones")
            conn = sqlite3.connect("Inventario.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, nombre_empresa, estado, proximo_pago FROM usuarios WHERE username != 'Brandon'")
            clientes = cursor.fetchall()
            
            if not clientes:
                st.info("Aún no hay empresas registradas.")
            else:
                hoy = datetime.date.today()
                for cli in clientes:
                    cli_id, u_name, n_empresa, estado, p_pago_str = cli
                    p_pago = datetime.datetime.strptime(p_pago_str, "%Y-%m-%d").date()
                    dias_restantes = (p_pago - hoy).days
                    
                    with st.expander(f"🏢 {n_empresa.upper()} - ID: {cli_id}"):
                        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                        with col1:
                            st.write(f"**Próximo Pago:** {p_pago_str}")
                            if dias_restantes < 0:
                                st.error(f"⚠️ En Mora")
                            else:
                                st.success(f"✅ {dias_restantes} días rest.")
                        with col2:
                            st.write(f"**Estado:** {estado}")
                            if estado == "Activo":
                                if st.button("🔴 Suspender", key=f"susp_{cli_id}"):
                                    cursor.execute("UPDATE usuarios SET estado = 'Suspendido' WHERE id = ?", (cli_id,))
                                    conn.commit()
                                    st.rerun()
                            else:
                                if st.button("🟢 Activar", key=f"act_{cli_id}"):
                                    cursor.execute("UPDATE usuarios SET estado = 'Activo' WHERE id = ?", (cli_id,))
                                    conn.commit()
                                    st.rerun()
                        with col3:
                            nueva_fecha = st.date_input("Extender hasta:", value=p_pago, key=f"date_{cli_id}")
                            if st.button("💾 Guardar Fecha", key=f"btn_date_{cli_id}"):
                                cursor.execute("UPDATE usuarios SET proximo_pago = ? WHERE id = ?", (nueva_fecha.strftime("%Y-%m-%d"), cli_id))
                                conn.commit()
                                rerun_ok = True
                                st.rerun()
                        with col4:
                            if st.button("🗑️ Eliminar", key=f"del_{cli_id}"):
                                if eliminar_negocio_db(cli_id):
                                    st.rerun()
            conn.close()

        with tab2:
            st.subheader("Crear Cuenta para un nuevo Negocio")
            with st.form("registro_empresa_form"):
                new_user = st.text_input("Usuario")
                new_pass = st.text_input("Contraseña", type="password")
                new_name = st.text_input("Nombre Comercial")
                fecha_limite = st.date_input("Primer Pago Límite", value=datetime.date.today() + datetime.timedelta(days=30))
                btn_registrar = st.form_submit_button("Registrar Cliente")
                
                if btn_registrar and new_user and new_pass and new_name:
                    try:
                        conn = sqlite3.connect("Inventario.db")
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO usuarios (username, password, nombre_empresa, estado, proximo_pago) VALUES (?, ?, ?, 'Activo', ?)",
                            (new_user, new_pass, new_name, fecha_limite.strftime("%Y-%m-%d"))
                        )
                        conn.commit()
                        conn.close()
                        st.success(f"¡{new_name} registrado!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("El usuario ya existe.")

    # ==========================================
    # 🏢 PERFIL DE CLIENTE (CON MENÚ MODULAR)
    # ==========================================
    else:
        # CANDADO DE SEGURIDAD EN TIEMPO REAL
        conn_verificar = sqlite3.connect("Inventario.db")
        cursor_verificar = conn_verificar.cursor()
        cursor_verificar.execute("SELECT estado, proximo_pago FROM usuarios WHERE username = ?", (st.session_state.username,))
        datos_suscripcion = cursor_verificar.fetchone()
        conn_verificar.close()
        
        hoy_actual = datetime.date.today().strftime("%Y-%m-%d")
        if datos_suscripcion:
            estado_actual, pago_actual = datos_suscripcion
            if estado_actual == "Suspendido" or pago_actual < hoy_actual:
                st.error("❌ **Servicio Interrumpido.** Tu suscripción ha vencido o ha sido suspendida. Contacta a Brandon.")
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.session_state.perfil = ""
                st.session_state.empresa = ""
                if st.button("Volver al Inicio"):
                    st.rerun()
                st.stop()

        st.sidebar.divider()
        st.sidebar.subheader("🎯 Menú de Operaciones")
        
        opcion = st.sidebar.radio(
            "Selecciona una opción:",
            [
                "📋 Ver Inventario",
                "➕ Registrar y Modificar Productos",
                "🛒 Registrar Ventas",
                "💰 Ganancias del Día",
                "📈 Reporte Trimestral & Top"
            ]
        )
        
        st.sidebar.divider()
        st.sidebar.button("🚪 Cerrar Sesión", on_click=cerrar_sesion, use_container_width=True)

        conn = sqlite3.connect("Inventario.db")
        cursor = conn.cursor()
        hoy_str = datetime.date.today().strftime("%Y-%m-%d")

        # --- MÓDULO 1: VER INVENTARIO ---
        if opcion == "📋 Ver Inventario":
            st.title("📋 Inventario Actual de Productos")
            cursor.execute("SELECT nombre_producto, precio, cantidad FROM productos WHERE empresa = ?", (st.session_state.username,))
            mis_productos = cursor.fetchall()
            
            if mis_productos:
                st.table([{"Producto": p[0], "Precio": f"${p[1]:,.0f}", "Stock Disponible": p[2]} for p in mis_productos])
            else:
                st.info("No tienes productos registrados en tu inventario.")

        # --- MÓDULO 2: REGISTRAR Y MODIFICAR PRODUCTOS ---
        elif opcion == "➕ Registrar y Modificar Productos":
            st.title("➕ Gestión de Catálogo de Productos")
            
            sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Añadir Producto Nuevo", "🔧 Editar Producto Existente", "🗑️ Remover del Catálogo"])
            
            with sub_tab1:
                st.subheader("Registrar un artículo nuevo")
                with st.form("add_product_form", clear_on_submit=True):
                    prod_nombre = st.text_input("Nombre del Artículo / Producto")
                    prod_precio = st.number_input("Precio de Venta ($)", min_value=0.0, step=500.0)
                    prod_cant = st.number_input("Cantidad Inicial en Stock", min_value=0, step=1)
                    btn_add_prod = st.form_submit_button("💾 Guardar Nuevo")
                    
                    if btn_add_prod and prod_nombre:
                        cursor.execute(
                            "INSERT INTO productos (empresa, nombre_producto, precio, cantidad) VALUES (?, ?, ?, ?)",
                            (st.session_state.username, prod_nombre, prod_precio, prod_cant)
                        )
                        conn.commit()
                        st.success(f"¡{prod_nombre} añadido al inventario con éxito!")
                        # Se usa toast para notificación rápida y se refresca para actualizar las demás pestañas instantáneamente
                        st.toast(f"Producto {prod_nombre} guardado correctamente.")
                        st.rerun()

            with sub_tab2:
                st.subheader("🔧 Modificar datos o reabastecer inventario")
                cursor.execute("SELECT id, nombre_producto, precio, cantidad FROM productos WHERE empresa = ?", (st.session_state.username,))
                prods_editar = cursor.fetchall()
                
                if prods_editar:
                    dict_prods = {p[1]: (p[0], p[2], p[3]) for p in prods_editar}
                    p_a_editar = st.selectbox("Selecciona el producto que deseas modificar", list(dict_prods.keys()))
                    
                    id_edit, precio_edit, cant_edit = dict_prods[p_a_editar]
                    
                    with st.form("edit_product_form"):
                        nuevo_nombre = st.text_input("Nombre del Producto", value=p_a_editar)
                        nuevo_precio = st.number_input("Precio ($)", min_value=0.0, value=precio_edit, step=500.0)
                        nueva_cantidad = st.number_input("Stock Actualizado (Unidades)", min_value=0, value=cant_edit, step=1)
                        btn_update_prod = st.form_submit_button("💾 Actualizar Cambios")
                        
                        if btn_update_prod and nuevo_nombre:
                            cursor.execute(
                                "UPDATE productos SET nombre_producto = ?, precio = ?, cantidad = ? WHERE id = ?",
                                (nuevo_nombre, nuevo_precio, nueva_cantidad, id_edit)
                            )
                            conn.commit()
                            st.success(f"¡{nuevo_nombre} actualizado de forma exitosa!")
                            st.rerun()
                else:
                    st.info("Aún no tienes productos para modificar.")

            with sub_tab3:
                st.subheader("🗑️ Eliminar productos del catálogo")
                cursor.execute("SELECT id, nombre_producto FROM productos WHERE empresa = ?", (st.session_state.username,))
                prods_eliminar = cursor.fetchall()
                
                if prods_eliminar:
                    dict_eliminar = {p[1]: p[0] for p in prods_eliminar}
                    p_a_eliminar = st.selectbox("Selecciona el producto que deseas eliminar definitivamente", list(dict_eliminar.keys()))
                    id_eliminar = dict_eliminar[p_a_eliminar]
                    
                    st.warning(f"⚠️ **Atención:** Al eliminar **{p_a_eliminar}**, este desaparecerá por completo de tu inventario actual.")
                    
                    with st.form("delete_product_form"):
                        pass_confirmar_del = st.text_input("Introduce tu contraseña para confirmar la eliminación:", type="password")
                        btn_delete_prod = st.form_submit_button("🚨 Eliminar Definitivamente", type="primary")
                        
                        if btn_delete_prod:
                            if verificar_password_usuario(st.session_state.username, pass_confirmar_del):
                                cursor.execute("DELETE FROM productos WHERE id = ?", (id_eliminar,))
                                conn.commit()
                                st.success(f"El producto '{p_a_eliminar}' ha sido removido del catálogo.")
                                st.rerun()
                            else:
                                st.error("Contraseña incorrecta. No se pudo eliminar el producto.")
                else:
                    st.info("No tienes productos en tu catálogo para remover.")

       # --- MÓDULO 3: REGISTRAR VENTAS ---
        elif opcion == "🛒 Registrar Ventas":
            st.title("🛒 Terminal de Registro de Ventas")
            cursor.execute("SELECT nombre_producto, precio, cantidad FROM productos WHERE empresa = ?", (st.session_state.username,))
            prods_disponibles = cursor.fetchall()
            
            if prods_disponibles:
                nombres_p = [p[0] for p in prods_disponibles]
                dict_precios = {p[0]: p[1] for p in prods_disponibles}
                dict_stocks = {p[0]: p[2] for p in prods_disponibles}
                
                # --- AQUÍ EMPIEZA EL CAMBIO (Quitamos el st.form) ---
                p_seleccionado = st.selectbox("Selecciona el producto", nombres_p)
                
                stock_disponible = dict_stocks[p_seleccionado]
                st.info(f"📦 Stock actual disponible de este artículo: **{stock_disponible}** unidades.")
                
                cant_vendida = st.number_input("Cantidad Vendida", min_value=1, value=1, step=1)
                
                if st.button("⚡ Procesar Venta", type="primary", use_container_width=True):
                    if cant_vendida > stock_disponible:
                        st.error(f"❌ **Error de Inventario:** No puedes vender {cant_vendida} unidades. Solo quedan {stock_disponible} en stock.")
                    else:
                        total_venta = dict_precios[p_seleccionado] * cant_vendida
                        
                        cursor.execute(
                            "INSERT INTO ventas (empresa, producto, cantidad, total, fecha, caja_cerrada) VALUES (?, ?, ?, ?, ?, 0)",
                            (st.session_state.username, p_seleccionado, cant_vendida, total_venta, hoy_str)
                        )
                        
                        cursor.execute(
                            "UPDATE productos SET cantidad = cantidad - ? WHERE empresa = ? AND nombre_producto = ?",
                            (cant_vendida, st.session_state.username, p_seleccionado)
                        )
                        
                        conn.commit()
                        st.success(f"¡Venta procesada con éxito! Se descontaron {cant_vendida} unidades. Total: ${total_venta:,.0f}")
                        st.rerun()
                # --- AQUÍ TERMINA EL CAMBIO ---
            else:
                st.warning("Debes registrar productos antes de poder realizar una venta.")

        # --- MÓDULO 4: GANANCIAS DEL DÍA ---
        elif opcion == "💰 Ganancias del Día":
            st.title("💰 Control de Ganancias Diarias y Caja Abierta")
            
            cursor.execute("SELECT id, producto, cantidad, total, fecha FROM ventas WHERE empresa = ? AND fecha = ? AND caja_cerrada = 0", (st.session_state.username, hoy_str))
            ventas_dia = cursor.fetchall()
            
            cursor.execute("SELECT SUM(total) FROM ventas WHERE empresa = ? AND fecha = ? AND caja_cerrada = 0", (st.session_state.username, hoy_str))
            total_dia = cursor.fetchone()[0] or 0.0
            
            st.metric("💰 Total en Caja Actual", f"${total_dia:,.0f}")
            
            st.subheader("📋 Ventas Activas de este Turno")
            if ventas_dia:
                for v in ventas_dia:
                    v_id, v_prod, v_cant, v_total, v_fecha = v
                    with st.expander(f"• {v_prod} ({v_cant} unds) - Total: ${v_total:,.0f} (ID Venta: {v_id})"):
                        
                        tipo_borrado = st.radio(f"¿Cómo deseas modificar la venta {v_id}?", ["Anulación Completa", "Devolución Parcial por Unidades"], key=f"tipo_b_{v_id}")
                        
                        unds_a_devolver = 0
                        if tipo_borrado == "Devolución Parcial por Unidades":
                            unds_a_devolver = st.number_input("¿Cuántas unidades se van a devolver?", min_value=1, max_value=int(v_cant)-1, value=1, step=1, key=f"dev_u_{v_id}")
                            st.caption(f"Se mantendrán **{v_cant - unds_a_devolver}** unidades en la venta.")
                        
                        col_t, col_b = st.columns([3, 1])
                        with col_t:
                            pass_confirmar = st.text_input("Contraseña de Seguridad para autorizar:", type="password", key=f"pwd_dia_{v_id}")
                        with col_b:
                            st.write("")
                            if st.button("💾 Aplicar Cambio", key=f"btn_dia_{v_id}", use_container_width=True):
                                if verificar_password_usuario(st.session_state.username, pass_confirmar):
                                    if tipo_borrado == "Anulación Completa":
                                        cursor.execute("UPDATE productos SET cantidad = cantidad + ? WHERE empresa = ? AND nombre_producto = ?", (v_cant, st.session_state.username, v_prod))
                                        cursor.execute("DELETE FROM ventas WHERE id = ?", (v_id,))
                                        st.success("Venta anulada por completo.")
                                    else:
                                        precio_unitario = v_total / v_cant
                                        nueva_cant_venta = v_cant - unds_a_devolver
                                        nuevo_total_dinero = precio_unitario * nueva_cant_venta
                                        
                                        cursor.execute("UPDATE productos SET cantidad = cantidad + ? WHERE empresa = ? AND nombre_producto = ?", (unds_a_devolver, st.session_state.username, v_prod))
                                        cursor.execute("UPDATE ventas SET cantidad = ?, total = ? WHERE id = ?", (nueva_cant_venta, nuevo_total_dinero, v_id))
                                        st.success(f"Devolución procesada. Se regresaron {unds_a_devolver} unidades al inventario.")
                                    
                                    conn.commit()
                                    st.rerun()
                                else:
                                    st.error("Contraseña Incorrecta.")
                
                st.divider()
                st.write("**🔒 Cierre de Turno / Caja**")
                pass_cierre = st.text_input("Ingresa tu contraseña para CERRAR LA CAJA del día:", type="password", key="cierre_caja_pwd")
                
                if st.button("🔒 Ejecutar Cierre de Caja", type="primary"):
                    if verificar_password_usuario(st.session_state.username, pass_cierre):
                        cursor.execute("UPDATE ventas SET caja_cerrada = 1 WHERE empresa = ? AND fecha = ?", (st.session_state.username, hoy_str))
                        conn.commit()
                        st.success("¡Caja cerrada correctamente!")
                        st.rerun()
                    else:
                        st.error("Contraseña de autorización inválida.")
            else:
                st.info("No hay ventas registradas en el turno actual de hoy.")

        # --- MÓDULO 5: REPORTES ---
        elif opcion == "📈 Reporte Trimestral & Top":
            st.title("📈 Inteligencia de Negocio e Historial (Nube)")
            
            hace_90_dias_str = (datetime.date.today() - datetime.timedelta(days=90)).strftime("%Y-%m-%d")
            
            cursor.execute("SELECT SUM(total) FROM ventas WHERE empresa = ? AND fecha >= ?", (st.session_state.username, hace_90_dias_str))
            ganancia_trimestral = cursor.fetchone()[0] or 0.0
            
            cursor.execute("""
                SELECT producto, SUM(cantidad) as total_unidades_vendidas 
                FROM ventas 
                WHERE empresa = ? 
                GROUP BY producto 
                ORDER BY total_unidades_vendidas DESC 
                LIMIT 1
            """, (st.session_state.username,))
            producto_top = cursor.fetchone()
            
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.metric("🗓️ Ganancias Totales Trimestre (90d)", f"${ganancia_trimestral:,.0f}")
            with col_m2:
                if producto_top:
                    st.metric("🏆 Producto Más Vendido (Estrella)", f"{producto_top[0]}", f"{producto_top[1]} unidades totales")
                else:
                    st.metric("🏆 Producto Más Vendido (Estrella)", "Sin datos aún")
            
            st.divider()
            st.subheader("📋 Panel de Control de Ventas Históricas (Nube)")
            
            cursor.execute("SELECT id, producto, cantidad, total, fecha, caja_cerrada FROM ventas WHERE empresa = ? ORDER BY id DESC", (st.session_state.username,))
            historial_nube = cursor.fetchall()
            
            if historial_nube:
                for h in historial_nube:
                    v_id, v_prod, v_cant, v_total, v_fecha, v_cerrada = h
                    estado_texto = "🔒 Histórica" if v_cerrada == 1 else "🔓 Turno Activo"
                    
                    with st.expander(f"📌 [{estado_texto}] {v_prod} ({v_cant} unds) - ${v_total:,.0f} | Fecha: {v_fecha} (ID: {v_id})"):
                        
                        tipo_borrado_n = st.radio(f"Acción para registro histórico {v_id}:", ["Anulación Completa", "Devolución Parcial por Unidades"], key=f"tipo_n_{v_id}")
                        
                        unds_a_devolver_n = 0
                        if tipo_borrado_n == "Devolución Parcial por Unidades":
                            unds_a_devolver_n = st.number_input("¿Cuántas unidades se van a devolver?", min_value=1, max_value=int(v_cant)-1, value=1, step=1, key=f"dev_n_{v_id}")
                        
                        col_txt_n, col_btn_n = st.columns([3, 1])
                        with col_txt_n:
                            pass_nube = st.text_input("Contraseña Maestra para autorizar:", type="password", key=f"pwd_nube_{v_id}")
                        with col_btn_n:
                            st.write("")
                            if st.button("🗑️ Aplicar en Nube", key=f"del_nube_{v_id}", use_container_width=True):
                                if verificar_password_usuario(st.session_state.username, pass_nube):
                                    if tipo_borrado_n == "Anulación Completa":
                                        cursor.execute("UPDATE productos SET cantidad = cantidad + ? WHERE empresa = ? AND nombre_producto = ?", (v_cant, st.session_state.username, v_prod))
                                        cursor.execute("DELETE FROM ventas WHERE id = ?", (v_id,))
                                        st.success("Registro histórico eliminado de forma permanente.")
                                    else:
                                        precio_unitario = v_total / v_cant
                                        nueva_cant_venta = v_cant - unds_a_devolver_n
                                        nuevo_total_dinero = precio_unitario * nueva_cant_venta
                                        
                                        cursor.execute("UPDATE productos SET cantidad = cantidad + ? WHERE empresa = ? AND nombre_producto = ?", (unds_a_devolver_n, st.session_state.username, v_prod))
                                        cursor.execute("UPDATE ventas SET cantidad = ?, total = ? WHERE id = ?", (nueva_cant_venta, nuevo_total_dinero, v_id))
                                        st.success("Devolución histórica aplicada y stock reintegrado.")
                                    
                                    conn.commit()
                                    st.rerun()
                                else:
                                    st.error("Contraseña Incorrecta.")
            else:
                st.caption("No hay registros en el histórico general.")

        conn.close()


        