"""CLI de línea de comandos."""
import argparse
from .lg import apagar_lg, cancelar_temporizador_lg, encender_lg, lg_cine, lg_descanso, lg_dia, lg_juego, lg_mute, lg_noche, lg_solo_audio, lg_volumen
from .scenes import apagar_ambas_tvs, apagar_m4, cancelar_todos_temporizadores, dormir_m4, encender_ambas, modo_cine, modo_descanso, modo_dia, modo_juego, modo_noche
from .status import estado_sistema
from .xiaomi import apagar_xiaomi, cancelar_temporizador_xiaomi, encender_xiaomi, xiaomi_cine, xiaomi_descanso, xiaomi_dia, xiaomi_juego, xiaomi_mute, xiaomi_noche, xiaomi_volumen


def main():
    parser = argparse.ArgumentParser(description="Sistema Maestro de Control: Mac M4 + LG 65\" + Xiaomi TV")
    
    # Comandos Conjuntos
    parser.add_argument("--encender", "--encender-tvs", action="store_true", help="Encender/Despertar ambas televisiones")
    parser.add_argument("--apagar-tvs", action="store_true", help="Apagar ambas televisiones")
    parser.add_argument("--modo-noche", nargs="?", const=90.0, type=float, help="Retroiluminación al 6%% + Temporizador (por defecto 90m) en ambas")
    parser.add_argument("--modo-dia", action="store_true", help="Retroiluminación al 100%% en ambas")
    parser.add_argument("--modo-cine", action="store_true", help="Modo Cine (Filmmaker en LG, Cine en Xiaomi) en ambas")
    parser.add_argument("--modo-juego", action="store_true", help="Modo Juego ultra baja latencia en ambas")
    parser.add_argument("--modo-descanso", action="store_true", help="Modo Descanso Visual (Filtro luz azul) en ambas")
    parser.add_argument("--cancelar-timer", action="store_true", help="Cancelar temporizadores en ambas teles")
    
    # Comandos Individuales LG 65"
    parser.add_argument("--encender-lg", action="store_true", help="Encender/Despertar LG 65\" via WoL")
    parser.add_argument("--lg-noche", nargs="?", const=90.0, type=float, help="Modo Noche (6%% + Timer 1.5h) solo en LG")
    parser.add_argument("--lg-dia", action="store_true", help="Modo Día (100%% brillo) solo en LG")
    parser.add_argument("--lg-cine", action="store_true", help="Filmmaker Mode D65 solo en LG")
    parser.add_argument("--lg-juego", action="store_true", help="Game Optimizer (~9ms lag) solo en LG")
    parser.add_argument("--lg-descanso", action="store_true", help="Descanso visual (Confort ocular) solo en LG")
    parser.add_argument("--lg-solo-audio", action="store_true", help="Apagar panel de la LG manteniendo audio")
    parser.add_argument("--apagar-lg", action="store_true", help="Apagar solo la LG 65\"")
    parser.add_argument("--cancelar-timer-lg", action="store_true", help="Cancelar temporizador de la LG")
    parser.add_argument("--lg-volumen", type=int, help="Ajustar volumen de la LG (0-100)")
    parser.add_argument("--lg-mute", action="store_true", help="Silenciar la LG")

    # Comandos Individuales Xiaomi TV
    parser.add_argument("--encender-xiaomi", action="store_true", help="Encender/Despertar Xiaomi TV via WoL y ADB")
    parser.add_argument("--xiaomi-noche", nargs="?", const=90.0, type=float, help="Modo Noche (6%% + Timer 1.5h) solo en Xiaomi")
    parser.add_argument("--xiaomi-dia", action="store_true", help="Modo Día (100%% brillo) solo en Xiaomi")
    parser.add_argument("--xiaomi-cine", action="store_true", help="Modo Película solo en Xiaomi")
    parser.add_argument("--xiaomi-juego", action="store_true", help="Modo Juego (ALLM) solo en Xiaomi")
    parser.add_argument("--xiaomi-descanso", action="store_true", help="Descanso visual solo en Xiaomi")
    parser.add_argument("--apagar-xiaomi", action="store_true", help="Apagar solo la Xiaomi TV")
    parser.add_argument("--cancelar-timer-xiaomi", action="store_true", help="Cancelar temporizador de la Xiaomi")
    parser.add_argument("--xiaomi-volumen", type=int, help="Ajustar volumen de Xiaomi (0-15)")
    parser.add_argument("--xiaomi-mute", action="store_true", help="Silenciar Xiaomi TV")

    # Mac M4
    parser.add_argument("--apagar-m4", action="store_true", help="Apagar completamente el Mac M4")
    parser.add_argument("--dormir-m4", action="store_true", help="Poner el Mac M4 en reposo")

    # Estado
    parser.add_argument("--status", action="store_true", help="Diagnóstico de estado y temporizadores")

    args = parser.parse_args()

    # Evaluación de comandos
    if args.status:
        estado_sistema()
    elif args.encender:
        encender_ambas()
    elif args.encender_lg:
        encender_lg()
    elif args.encender_xiaomi:
        encender_xiaomi()
    # Conjuntos
    elif args.apagar_tvs:
        apagar_ambas_tvs()
    elif args.modo_noche is not None:
        modo_noche(args.modo_noche)
    elif args.modo_dia:
        modo_dia()
    elif args.modo_cine:
        modo_cine()
    elif args.modo_juego:
        modo_juego()
    elif args.modo_descanso:
        modo_descanso()
    elif args.cancelar_timer:
        cancelar_todos_temporizadores()
    # LG Individual
    elif args.lg_noche is not None:
        lg_noche(args.lg_noche)
    elif args.lg_dia:
        lg_dia()
    elif args.lg_cine:
        lg_cine()
    elif args.lg_juego:
        lg_juego()
    elif args.lg_descanso:
        lg_descanso()
    elif args.lg_solo_audio:
        lg_solo_audio()
    elif args.apagar_lg:
        apagar_lg()
    elif args.cancelar_timer_lg:
        cancelar_temporizador_lg()
    elif args.lg_volumen is not None:
        lg_volumen(args.lg_volumen)
    elif args.lg_mute:
        lg_mute()
    # Xiaomi Individual
    elif args.xiaomi_noche is not None:
        xiaomi_noche(args.xiaomi_noche)
    elif args.xiaomi_dia:
        xiaomi_dia()
    elif args.xiaomi_cine:
        xiaomi_cine()
    elif args.xiaomi_juego:
        xiaomi_juego()
    elif args.xiaomi_descanso:
        xiaomi_descanso()
    elif args.apagar_xiaomi:
        apagar_xiaomi()
    elif args.cancelar_timer_xiaomi:
        cancelar_temporizador_xiaomi()
    elif args.xiaomi_volumen is not None:
        xiaomi_volumen(args.xiaomi_volumen)
    elif args.xiaomi_mute:
        xiaomi_mute()
    # Mac M4
    elif args.apagar_m4:
        apagar_m4()
    elif args.dormir_m4:
        dormir_m4()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
