import streamlit as st
import datetime
from supabase import create_client, Client

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Sistema de Gestión Comercial Cloud", page_icon="💼", layout="wide")

# --- CREDENCIALES DE SUPABASE ---
# Nota: La URL se compone usando la referencia 'vvvjddoiraljjtqxokcc' extraída del token anon
SUPABASE_URL = "https://vvvjddoiraljjtxqokcc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ2dmpkZG9pcmFsamp0eHFva2NjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE4OTU3NjYsImV4cCI6MjA5NzQ3MTc2Nn0.GEB41w3qq-tjKd55jZSie2In7JPqv75J6gGgAcrF2Nc"

@st.cache_resource
def obtener_cliente_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = obtener_cliente_supabase()

# --- FUNCIONES DE CONTROL DE SUSCRIPCIÓN Y SEGURIDAD ---

def verificar_y_actualizar_suscripcion(usuario_data):
    """
    Verifica si la mensualidad venció. Si venció y seguía 'Activo',
    lo suspende inmediatamente en la base de datos y actualiza el estado.
    """
    if not usuario_data:
        return None

    username = usuario_data.get("username")
    estado = usuario_data.get("estado")
    proximo_pago_str = usuario_data.get("proximo_pago")
    
    # El administrador Brandon es inmune a la suspensión automática
    if username == "Brandon":
        return usuario_data

    hoy = datetime.date.today()
    proximo_pago = datetime.datetime.strptime(proximo_pago_str, "%Y-%m-%d").date()

    if proximo_pago < hoy and estado == "Activo":
        # Ejecutar la desactivación automática en la base de datos
        supabase.table("usuarios")\
            .update({"estado": "Suspendido"})\
            .eq("id", usuario_data["id"])\
            .execute()
        
        usuario_data["estado"] = "Suspendido"
    
    return usuario_data

def login_user(user, pwd):
    response = supabase.table("usuarios")\
        .select("id, username, password, nombre_empresa, estado, proximo_pago")\
        .eq("username", user)\
        .eq("password", pwd)\
        .execute()
    
    if response.data:
        # Pasar por el filtro de verificación de mensualidad al autenticar
        return verificar_y_actualizar_suscripcion(response.data[0])
    return None

def verificar_password_por_id(user_id, pwd):
    response = supabase.table("usuarios")\
        .select("id")\
        .eq("id", user_id)\
        .eq("password", pwd)\
        .execute()
    return len(response.data) > 0

# --- MANEJO DE SESIÓN EN STREAMLIT ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = ""
    st.session_state.perfil = ""
    st.session_state.empresa = ""

# --- INTERFAZ DE LOG IN ---
if not st.session_state.logged_in:
    st.title("🔑 Sistema Cloud - Iniciar Sesión")
    
    with st.form("login_form"):
        usuario_input = st.text_input("Usuario (Empresa)")
        clave_input = st.text_input("Contraseña", type="password")
        boton_entrar = st.form_submit_button("Ingresar al Sistema")
        
        if boton_entrar:
            user_data = login_user(usuario_input, clave_input)
            if user_data:
                if user_data["estado"] == "Suspendido":
                    st.error("❌ **Servicio Interrumpido.** Tu suscripción ha vencido o está suspendida. Contacta a Brandon para activar el servicio.")
                else:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_data["id"]
                    st.session_state.username = user_data["username"]
                    st.session_state.empresa = user_data["nombre_empresa"]
                    st.session_state.perfil = "admin" if user_data["username"] == "Brandon" else "cliente"
                    st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

# --- INTERFAZ DEL PROGRAMA AUTENTICADO ---
else:
    st.sidebar.title(f"🏢 {st.session_state.empresa}")
    st.sidebar.caption(f"👤 Usuario: {st.session_state.username}")
    
    def cerrar_sesion():
        st.session_state.logged_in = False
        st.session_state.user_id = None
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
        
        tab1, tab2 = st.tabs(["📊 Monitorear Clientes", "➕ Registrar Nueva Empresa"])
        
        with tab1:
            st.subheader("Estado de Clientes y Suscripciones en la Nube")
            # Traer todos los clientes excepto al admin
            response = supabase.table("usuarios").select("*").neq("username", "Brandon").order("id").execute()
            clientes = response.data
            
            if not clientes:
                st.info("Aún no hay empresas registradas.")
            else:
                hoy = datetime.date.today()
                for cli in clientes:
                    # Filtro pasivo por si el admin visualiza un cliente que ya expiró hoy
                    cli = verificar_y_actualizar_suscripcion(cli)
                    
                    cli_id = cli["id"]
                    u_name = cli["username"]
                    n_empresa = cli["nombre_empresa"]
                    estado = cli["estado"]
                    p_pago_str = cli["proximo_pago"]
                    
                    p_pago = datetime.datetime.strptime(p_pago_str, "%Y-%m-%d").date()
                    dias_restantes = (p_pago - hoy).days
                    
                    with st.expander(f"🏢 {n_empresa.upper()} - ID: {cli_id} ({estado})"):
                        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                        with col1:
                            st.write(f"**Próximo Pago:** {p_pago_str}")
                            if dias_restantes < 0:
                                st.error("⚠️ En Mora / Suspendido")
                            else:
                                st.success(f"✅ {dias_restantes} días restantes")
                        with col2:
                            st.write(f"**Acción de Estado:**")
                            if estado == "Activo":
                                if st.button("🔴 Suspender", key=f"susp_{cli_id}"):
                                    supabase.table("usuarios").update({"estado": "Suspendido"}).eq("id", cli_id).execute()
                                    st.rerun()
                            else:
                                if st.button("🟢 Activar", key=f"act_{cli_id}"):
                                    supabase.table("usuarios").update({"estado": "Activo"}).eq("id", cli_id).execute()
                                    st.rerun()
                        with col3:
                            nueva_fecha = st.date_input("Extender hasta:", value=p_pago, key=f"date_{cli_id}")
                            if st.button("💾 Guardar Fecha", key=f"btn_date_{cli_id}"):
                                supabase.table("usuarios").update({"proximo_pago": nueva_fecha.strftime("%Y-%m-%d")}).eq("id", cli_id).execute()
                                st.rerun()
                        with col4:
                            if st.button("🗑️ Eliminar", key=f"del_{cli_id}"):
                                supabase.table("usuarios").delete().eq("id", cli_id).execute()
                                st.rerun()

        with tab2:
            st.subheader("Crear Cuenta para un nuevo Negocio")
            with st.form("registro_empresa_form"):
                new_user = st.text_input("Usuario")
                new_pass = st.text_input("Contraseña", type="password")
                new_name = st.text_input("Nombre Comercial")
                fecha_limite = st.date_input("Primer Pago Límite", value=datetime.date.today() + datetime.timedelta(days=30))
                btn_registrar = st.form_submit_button("Registrar Cliente")
                
                if btn_registrar and new_user and new_pass and new_name:
                    data_nuevo = {
                        "username": new_user,
                        "password": new_pass,
                        "nombre_empresa": new_name,
                        "estado": "Activo",
                        "proximo_pago": fecha_limite.strftime("%Y-%m-%d")
                    }
                    response_ins = supabase.table("usuarios").insert(data_nuevo).execute()
                    if response_ins.data:
                        st.success(f"¡{new_name} registrado en la nube con éxito!")
                        st.rerun()
                    else:
                        st.error("Error al registrar. Puede que el usuario ya exista.")

    # ==========================================
    # 🏢 PERFIL DE CLIENTE (MODULAR)
    # ==========================================
    else:
        # CANDADO EN TIEMPO REAL: Verificar estado actual directo desde Supabase antes de pintar cualquier módulo
        res_candado = supabase.table("usuarios").select("*").eq("id", st.session_state.user_id).execute()
        if res_candado.data:
            info_actualizada = verificar_y_actualizar_suscripcion(res_candado.data[0])
            if info_actualizada["estado"] == "Suspendido":
                st.error("❌ **Servicio Interrumpido.** Tu suscripción ha vencido. Contacta al administrador.")
                st.sidebar.button("🚪 Volver al Inicio", on_click=cerrar_sesion)
                st.stop()

        st.sidebar.divider()
        st.sidebar.subheader("🎯 Menú de Operaciones")
        opcion = st.sidebar.radio(
            "Selecciona una opción:",
            ["📋 Ver Inventario", "➕ Registrar y Modificar Productos", "🛒 Registrar Ventas", "💰 Ganancias del Día", "📈 Reporte Trimestral & Top"]
        )
        st.sidebar.divider()
        st.sidebar.button("🚪 Cerrar Sesión", on_click=cerrar_sesion, use_container_width=True)

        hoy_str = datetime.date.today().strftime("%Y-%m-%d")

        # --- MÓDULO 1: VER INVENTARIO ---
        if opcion == "📋 Ver Inventario":
            st.title("📋 Inventario Actual de Productos (Cloud)")
            res_prod = supabase.table("productos").select("nombre_producto, precio, cantidad").eq("usuario_id", st.session_state.user_id).execute()
            mis_productos = res_prod.data
            
            if mis_productos:
                st.table([{"Producto": p["nombre_producto"], "Precio": f"${p['precio']:,.0f}", "Stock Disponible": p["cantidad"]} for p in mis_productos])
            else:
                st.info("No tienes productos registrados en tu inventario.")

        # --- MÓDULO 2: REGISTRAR Y MODIFICAR PRODUCTOS ---
        elif opcion == "➕ Registrar y Modificar Productos":
            st.title("➕ Gestión de Catálogo de Productos")
            sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Añadir Producto Nuevo", "🔧 Editar Producto Existente", "🗑️ Remover del Catálogo"])
            
            with sub_tab1:
                with st.form("add_product_form", clear_on_submit=True):
                    prod_nombre = st.text_input("Nombre del Artículo")
                    prod_precio = st.number_input("Precio de Venta ($)", min_value=0.0, step=500.0)
                    prod_cant = st.number_input("Cantidad Inicial", min_value=0, step=1)
                    if st.form_submit_button("💾 Guardar Nuevo") and prod_nombre:
                        supabase.table("productos").insert({
                            "usuario_id": st.session_state.user_id,
                            "nombre_producto": prod_nombre,
                            "precio": prod_precio,
                            "cantidad": prod_cant
                        }).execute()
                        st.toast(f"Producto {prod_nombre} guardado en la nube.")
                        st.rerun()

            with sub_tab2:
                res_ed = supabase.table("productos").select("id, nombre_producto, precio, cantidad").eq("usuario_id", st.session_state.user_id).execute()
                prods_editar = res_ed.data
                
                if prods_editar:
                    dict_prods = {p["nombre_producto"]: (p["id"], p["precio"], p["cantidad"]) for p in prods_editar}
                    p_a_editar = st.selectbox("Selecciona el producto", list(dict_prods.keys()))
                    id_edit, precio_edit, cant_edit = dict_prods[p_a_editar]
                    
                    with st.form("edit_product_form"):
                        nuevo_nombre = st.text_input("Nombre del Producto", value=p_a_editar)
                        nuevo_precio = st.number_input("Precio ($)", min_value=0.0, value=float(precio_edit), step=500.0)
                        nueva_cantidad = st.number_input("Stock", min_value=0, value=int(cant_edit), step=1)
                        if st.form_submit_button("💾 Actualizar Cambios") and nuevo_nombre:
                            supabase.table("productos").update({
                                "nombre_producto": nuevo_nombre,
                                "precio": nuevo_precio,
                                "cantidad": nueva_cantidad
                            }).eq("id", id_edit).execute()
                            st.success(f"¡{nuevo_nombre} actualizado!")
                            st.rerun()

            with sub_tab3:
                res_el = supabase.table("productos").select("id, nombre_producto").eq("usuario_id", st.session_state.user_id).execute()
                prods_eliminar = res_el.data
                
                if prods_eliminar:
                    dict_eliminar = {p["nombre_producto"]: p["id"] for p in prods_eliminar}
                    p_a_eliminar = st.selectbox("Selecciona el producto a eliminar", list(dict_eliminar.keys()))
                    id_eliminar = dict_eliminar[p_a_eliminar]
                    
                    with st.form("delete_product_form"):
                        pass_confirmar_del = st.text_input("Contraseña de confirmación:", type="password")
                        if st.form_submit_button("🚨 Eliminar Definitivamente", type="primary"):
                            if verificar_password_por_id(st.session_state.user_id, pass_confirmar_del):
                                supabase.table("productos").delete().eq("id", id_eliminar).execute()
                                st.success("Producto eliminado.")
                                st.rerun()
                            else:
                                st.error("Contraseña incorrecta.")

        # --- MÓDULO 3: REGISTRAR VENTAS ---
        elif opcion == "🛒 Registrar Ventas":
            st.title("🛒 Terminal de Registro de Ventas")
            res_v = supabase.table("productos").select("id, nombre_producto, precio, cantidad").eq("usuario_id", st.session_state.user_id).execute()
            prods_disponibles = res_v.data
            
            if prods_disponibles:
                nombres_p = [p["nombre_producto"] for p in prods_disponibles]
                dict_datos = {p["nombre_producto"]: (p["id"], p["precio"], p["cantidad"]) for p in prods_disponibles}
                
                p_seleccionado = st.selectbox("Selecciona el producto", nombres_p)
                p_id, precio_p, stock_disponible = dict_datos[p_seleccionado]
                
                st.info(f"📦 Stock disponible: **{stock_disponible}** unidades.")
                cant_vendida = st.number_input("Cantidad Vendida", min_value=1, value=1, step=1)
                
                if st.button("⚡ Procesar Venta", type="primary", use_container_width=True):
                    if cant_vendida > stock_disponible:
                        st.error("❌ **Error de Inventario:** Stock insuficiente.")
                    else:
                        total_venta = precio_p * cant_vendida
                        # Insertar Venta
                        supabase.table("ventas").insert({
                            "usuario_id": st.session_state.user_id,
                            "producto": p_seleccionado,
                            "cantidad": cant_vendida,
                            "total": total_venta,
                            "fecha": hoy_str
                        }).execute()
                        
                        # Descontar Stock
                        supabase.table("productos").update({
                            "cantidad": stock_disponible - cant_vendida
                        }).eq("id", p_id).execute()
                        
                        st.success(f"¡Venta procesada! Total: ${total_venta:,.0f}")
                        st.rerun()

        # --- MÓDULO 4: GANANCIAS DEL DÍA ---
        elif opcion == "💰 Ganancias del Día":
            st.title("💰 Control de Ganancias Diarias")
            
            res_vd = supabase.table("ventas").select("id, producto, cantidad, total").eq("usuario_id", st.session_state.user_id).eq("fecha", hoy_str).eq("caja_cerrada", 0).execute()
            ventas_dia = res_vd.data
            
            total_dia = sum([v["total"] for v in ventas_dia]) if ventas_dia else 0.0
            st.metric("💰 Total en Caja Actual", f"${total_dia:,.0f}")
            
            if ventas_dia:
                for v in ventas_dia:
                    v_id = v["id"]
                    v_prod = v["producto"]
                    v_cant = v["cantidad"]
                    v_total = v["total"]
                    
                    with st.expander(f"• {v_prod} ({v_cant} unds) - Total: ${v_total:,.0f}"):
                        tipo_borrado = st.radio("Acción:", ["Anulación Completa", "Devolución Parcial"], key=f"t_b_{v_id}")
                        unds_a_devolver = 1
                        if tipo_borrado == "Devolución Parcial":
                            unds_a_devolver = st.number_input("Unidades a devolver:", min_value=1, max_value=int(v_cant)-1, value=1, key=f"d_u_{v_id}")
                        
                        pass_confirmar = st.text_input("Autorizar con contraseña:", type="password", key=f"pwd_{v_id}")
                        if st.button("Aplicar", key=f"btn_{v_id}"):
                            if verificar_password_por_id(st.session_state.user_id, pass_confirmar):
                                # Obtener stock actual del producto para reintegrar
                                res_p_stock = supabase.table("productos").select("id, cantidad").eq("usuario_id", st.session_state.user_id).eq("nombre_producto", v_prod).execute()
                                
                                if res_p_stock.data:
                                    prod_id = res_p_stock.data[0]["id"]
                                    stock_actual = res_p_stock.data[0]["cantidad"]
                                    
                                    if tipo_borrado == "Anulación Completa":
                                        supabase.table("productos").update({"cantidad": stock_actual + v_cant}).eq("id", prod_id).execute()
                                        supabase.table("ventas").delete().eq("id", v_id).execute()
                                    else:
                                        precio_u = v_total / v_cant
                                        nueva_cant = v_cant - unds_a_devolver
                                        supabase.table("productos").update({"cantidad": stock_actual + unds_a_devolver}).eq("id", prod_id).execute()
                                        supabase.table("ventas").update({"cantidad": nueva_cant, "total": precio_u * nueva_cant}).eq("id", v_id).execute()
                                    st.rerun()
                            else:
                                st.error("Contraseña incorrecta.")

                st.divider()
                pass_cierre = st.text_input("Contraseña para cerrar caja:", type="password")
                if st.button("🔒 Ejecutar Cierre de Caja", type="primary"):
                    if verificar_password_por_id(st.session_state.user_id, pass_cierre):
                        supabase.table("ventas").update({"caja_cerrada": 1}).eq("usuario_id", st.session_state.user_id).eq("fecha", hoy_str).execute()
                        st.success("Caja cerrada correctamente.")
                        st.rerun()

        # --- MÓDULO 5: REPORTES ---
        elif opcion == "📈 Reporte Trimestral & Top":
            st.title("📈 Inteligencia de Negocio")
            hace_90_dias = (datetime.date.today() - datetime.timedelta(days=90)).strftime("%Y-%m-%d")
            
            res_trim = supabase.table("ventas").select("total").eq("usuario_id", st.session_state.user_id).gte("fecha", hace_90_dias).execute()
            ganancia_trimestral = sum([v["total"] for v in res_trim.data]) if res_trim.data else 0.0
            
            # Traer ventas para calcular el producto más vendido de forma manual y simple
            res_all_v = supabase.table("ventas").select("producto, cantidad").eq("usuario_id", st.session_state.user_id).execute()
            
            top_prod, top_cant = "Sin datos", 0
            if res_all_v.data:
                conteo = {}
                for v in res_all_v.data:
                    conteo[v["producto"]] = conteo.get(v["producto"], 0) + v["cantidad"]
                if conteo:
                    top_prod = max(conteo, key=conteo.get)
                    top_cant = conteo[top_prod]
            
            col_m1, col_m2 = st.columns(2)
            col_m1.metric("🗓️ Ganancias Trimestrales (90d)", f"${ganancia_trimestral:,.0f}")
            col_m2.metric("🏆 Producto Estrella", top_prod, f"{top_cant} unidades" if top_cant > 0 else "")

            