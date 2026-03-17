import sys
from datetime import datetime
from sqlalchemy.future import select
from base_datos import crear_sesion, Usuario, CicloEscolar

async def registrar_nuevo_alumno():
    print("\n--- 1. DEFINICIÓN DEL CICLO ESCOLAR Y PERFIL ---")
    carrera_input = input("Ingresa la carrera a la que perteneces: ")
    semestre_input = input("Ingresa el semestre en el que te encuentras: ")
    ciclo_input = input("Ingresa el nombre del ciclo escolar (Ej. 2026-A): ")
    
    print("\nNota: Usa el formato AAAA-MM-DD (Ejemplo: 2026-01-19)")
    while True:
        inicio_str = input("Fecha de INICIO del ciclo escolar: ")
        fin_str = input("Fecha de FIN del ciclo escolar: ")
        try:
            fecha_inicio_real = datetime.strptime(inicio_str, "%Y-%m-%d").date()
            fecha_fin_real = datetime.strptime(fin_str, "%Y-%m-%d").date()
            
            # Validación lógica: El inicio no puede ser después del fin
            if fecha_inicio_real >= fecha_fin_real:
                print("\nError: La fecha de inicio debe ser ANTES que la fecha de fin. Intenta de nuevo.")
                continue
            break
        except ValueError:
            print("\nError: Formato de fecha incorrecto. Asegúrate de usar guiones (AAAA-MM-DD).")

    print("\n--- 2. REGISTRO DE DATOS PERSONALES ---")
    nombre_input = input("Ingresa tu nombre completo: ")
    correo_input = input("Ingresa tu correo electronico: ")
    codigo_input = input("Ingresa tu codigo de alumno: ")
    contra_input = input("Crea una contrasena: ")
    
    async with crear_sesion() as sesion_bd:
        # Guardamos usuario
        nuevo_usuario = Usuario(
            nombre=nombre_input, correo=correo_input,
            codigo_alumno=codigo_input, contrasena=contra_input
        )
        sesion_bd.add(nuevo_usuario)
        await sesion_bd.flush() # Obtenemos el ID generado del usuario
        
        # Guardamos el ciclo vinculado al usuario
        nuevo_ciclo = CicloEscolar(
            usuario_id=nuevo_usuario.id,
            carrera=carrera_input, semestre=semestre_input,
            nombre_ciclo=ciclo_input,
            fecha_inicio=fecha_inicio_real, fecha_fin=fecha_fin_real
        )
        sesion_bd.add(nuevo_ciclo)
        await sesion_bd.commit()
        
        print(f"\nRegistro exitoso. Bienvenido, {nuevo_usuario.nombre}")
        print(f"Ciclo '{nuevo_ciclo.nombre_ciclo}' configurado del {fecha_inicio_real} al {fecha_fin_real}.")
        return nuevo_usuario.id

async def iniciar_sesion():
    print("\n--- INICIAR SESIÓN ---")
    identificador = input("Ingresa tu correo o tu código de alumno: ")
    contra_input = input("Ingresa tu contraseña: ")
    
    async with crear_sesion() as sesion_bd:
        consulta = select(Usuario).where(
            ((Usuario.correo == identificador) | (Usuario.codigo_alumno == identificador)) & 
            (Usuario.contrasena == contra_input)
        )
        resultado = await sesion_bd.execute(consulta)
        usuario_encontrado = resultado.scalar_one_or_none()
        
        if usuario_encontrado:
            print(f"\nSesión iniciada correctamente. Hola de nuevo, {usuario_encontrado.nombre}")
            return usuario_encontrado.id
        else:
            print("\nError: Datos incorrectos. Inténtalo de nuevo.")
            return None

async def menu_acceso():
    print("=======================================")
    print(" BIENVENIDO A HERMES_APP ")
    print("=======================================")
    
    while True:
        print("\nElige una opcion:")
        print("1. Iniciar sesion")
        print("2. Registrarme como nuevo alumno")
        print("3. Salir")
        
        opcion = input("Tu eleccion (1/2/3): ")
        
        if opcion == "1":
            id_obtenido = await iniciar_sesion()
            if id_obtenido: return id_obtenido
        elif opcion == "2":
            id_obtenido = await registrar_nuevo_alumno()
            if id_obtenido: return id_obtenido
        elif opcion == "3":
            print("Saliendo del programa...")
            sys.exit()
        else:
            print("Opcion no valida.")