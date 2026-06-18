import streamlit as st
import sqlite3
import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Sistema de Gestión Comercial", page_icon="💼", layout="wide")

# --- CONEXIÓN Y CREACIÓN DE TABLAS (SQLITE) ---
def inicializar_bd():
    conn = sqlite3.connect("Inventario.db")
    cursor = conn.cursor()
    
    # 1. Tabla de Usuarios/Empresas (El candado de control)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        nombre_empresa TEXT,
        estado TEXT DEFAULT 'Activo', -- 'Activo' o 'Suspendido'
        proximo_pago DATE
    )
    """)
    
    # 2. Tabla de Productos (Filtrada por empresa para que no se mezclen)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa TEXT,
        nombre_producto TEXT,
        precio REAL,
        cantidad INTEGER
    )
    """)
    
    # Insertar al administrador por defecto usando OR IGNORE (Si ya existe, no hace nada)
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

# --- MANEJO DE SESIÓN EN STREAMLIT ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.perfil = ""
    st.session_state.empresa = ""

# --- FUNCIONES DE LOGÍSICA ---
def login_user(user, pwd):
    conn = sqlite3.connect("Inventario.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username, nombre_empresa, estado, proximo_pago FROM usuarios WHERE username = ? AND password = ?", (user, pwd))
    result = cursor.fetchone()
    conn.close()
    return result

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
                
                # Regla de oro: Si está suspendido o la fecha venció (y no eres tú)
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

# --- INTERFAZ DEL PROGRAMA (CUANDO YA INICIÓ SESIÓN) ---
else:
    # Barra lateral común para salir
    st.sidebar.subheader(f"👤 Conectado: {st.session_state.username}")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.perfil = ""
        st.session_state.empresa = ""
        st.rerun()

    # ==========================================
    # 👑 PERFIL DE ADMINISTRADOR (BRANDON)
    # ==========================================
    if st.session_state.perfil == "admin":
        st.title("👑 Panel de Control Supremo - Brandon Admin")
        st.write("Desde aquí controlas qué empresas tienen servicio activo y quiénes deben pagar.")
        
        tab1, tab2 = st.tabs(["📊 Monitorear y Modificar Clientes", "➕ Registrar Nueva Empresa"])
        
        with tab1:
            st.subheader("Estado de Clientes y Suscripciones")
            conn = sqlite3.connect("Inventario.db")
            cursor = conn.cursor()
            
            # Obtener todos los clientes (excluyendo tu usuario)
            cursor.execute("SELECT id, username, nombre_empresa, estado, proximo_pago FROM usuarios WHERE username != 'Brandon'")
            clientes = cursor.fetchall()
            
            if not clientes:
                st.info("Aún no hay empresas registradas en el sistema.")
            else:
                hoy = datetime.date.today()
                
                for cli in clientes:
                    cli_id, u_name, n_empresa, estado, p_pago_str = cli
                    p_pago = datetime.datetime.strptime(p_pago_str, "%Y-%m-%d").date()
                    dias_restantes = (p_pago - hoy).days
                    
                    # Contenedor visual para cada cliente
                    with st.expander(f"🏢 {n_empresa.upper()} (Usuario: {u_name})"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.write(f"**Próximo Pago:** {p_pago_str}")
                            if dias_restantes < 0:
                                st.error(f"⚠️ En Mora por {abs(dias_restantes)} días")
                            else:
                                st.success(f"✅ Le quedan {dias_restantes} días")
                                
                        with col2:
                            st.write(f"**Estado del Servicio:** {estado}")
                            # Botones para PONER o QUITAR servicio de una
                            if estado == "Activo":
                                if st.button("🔴 Suspender Servicio", key=f"susp_{cli_id}"):
                                    cursor.execute("UPDATE usuarios SET estado = 'Suspendido' WHERE id = ?", (cli_id,))
                                    conn.commit()
                                    st.rerun()
                            else:
                                if st.button("🟢 Activar Servicio", key=f"act_{cli_id}"):
                                    cursor.execute("UPDATE usuarios SET estado = 'Activo' WHERE id = ?", (cli_id,))
                                    conn.commit()
                                    st.rerun()
                                    
                        with col3:
                            # Extender la fecha de pago (Renovación)
                            nueva_fecha = st.date_input("Extender Pago hasta:", value=p_pago, key=f"date_{cli_id}")
                            if st.button("💾 Actualizar Fecha", key=f"btn_date_{cli_id}"):
                                cursor.execute("UPDATE usuarios SET proximo_pago = ? WHERE id = ?", (nueva_fecha.strftime("%Y-%m-%d"), cli_id))
                                conn.commit()
                                st.success("¡Suscripción actualizada!")
                                st.rerun()
            conn.close()

        with tab2:
            st.subheader("Crear Cuenta para un nuevo Negocio (SaaS)")
            with st.form("registro_empresa_form"):
                new_user = st.text_input("Usuario de Ingreso (ej: faraongym)")
                new_pass = st.text_input("Contraseña para el cliente", type="password")
                new_name = st.text_input("Nombre Comercial (ej: Gimnasio Faraón)")
                fecha_limite = st.date_input("Fecha del primer pago límite", value=datetime.date.today() + datetime.timedelta(days=30))
                
                btn_registrar = st.form_submit_button("Registrar Cliente")
                
                if btn_registrar:
                    if new_user and new_pass and new_name:
                        try:
                            conn = sqlite3.connect("Inventario.db")
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO usuarios (username, password, nombre_empresa, estado, proximo_pago) VALUES (?, ?, ?, 'Activo', ?)",
                                (new_user, new_pass, new_name, fecha_limite.strftime("%Y-%m-%d"))
                            )
                            conn.commit()
                            conn.close()
                            st.success(f"¡{new_name} registrado con éxito! Ya puede iniciar sesión.")
                        except sqlite3.IntegrityError:
                            st.error("El nombre de usuario ya existe. Elige otro.")
                    else:
                        st.warning("Por favor, llena todos los campos.")

    # ==========================================
    # 🏢 PERFIL DE CLIENTE (GIMNASIO, FERRETERÍA, ETC.)
    # ==========================================
    else:
        st.title(f"💼 Sistema de Gestión Comercial — {st.session_state.empresa}")
        st.write("Bienvenido a tu panel de administración local.")
        
        conn = sqlite3.connect("Inventario.db")
        cursor = conn.cursor()
        
        st.subheader("📦 Tus Productos")
        
        # Formulario para añadir producto propio
        with st.form("add_product_form"):
            prod_nombre = st.text_input("Nombre del Producto")
            prod_precio = st.number_input("Precio", min_value=0.0, step=500.0)
            prod_cant = st.number_input("Cantidad", min_value=0, step=1)
            btn_add_prod = st.form_submit_button("Añadir al Inventario")
            
            if btn_add_prod and prod_nombre:
                cursor.execute(
                    "INSERT INTO productos (empresa, nombre_producto, precio, cantidad) VALUES (?, ?, ?, ?)",
                    (st.session_state.username, prod_nombre, prod_precio, prod_cant)
                )
                conn.commit()
                st.success("Producto añadido.")
        
        # Mostrar solo los productos de esta empresa
        cursor.execute("SELECT nombre_producto, precio, cantidad FROM productos WHERE empresa = ?", (st.session_state.username,))
        mis_productos = cursor.fetchall()
        conn.close()
        
        if mis_productos:
            st.table([{"Producto": p[0], "Precio": f"${p[1]:,.0f}", "Cantidad": p[2]} for p in mis_productos])
        else:
            st.info("No tienes productos en tu inventario todavía.")
