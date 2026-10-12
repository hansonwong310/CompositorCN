#include <unistd.h>
#include <stdlib.h>
#include <libgen.h>
#include <mach-o/dyld.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char *argv[]) {
    char path[1024];
    uint32_t size = sizeof(path);
    if (_NSGetExecutablePath(path, &size) != 0) {
        return 1;
    }
    char *dir = dirname(path);
    char dylib[1024];
    char target[1024];
    snprintf(dylib, sizeof(dylib), "%s/CompositorZH.dylib", dir);
    snprintf(target, sizeof(target), "%s/Compositor_raw", dir);
    
    setenv("DYLD_INSERT_LIBRARIES", dylib, 1);
    return execv(target, argv);
}
