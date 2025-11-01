# ======================================================================
#               Subdirectories
# ======================================================================
add_subdirectory(arch)

# ======================================================================
#               Main Library
# ======================================================================
set(MODULE_NAME dmboot_main)
add_library(${MODULE_NAME} STATIC 
    main.c
)

target_link_libraries(${MODULE_NAME} 
    PRIVATE dmboot_inc
)

create_library_makefile(${MODULE_NAME})