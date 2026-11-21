# ExecuTorch JNI keep rules
# The native libexecutorch_jni.so looks up these classes by name via JNI reflection.
# R8 must not strip, obfuscate, or rename them.

-keep class org.pytorch.executorch.** { *; }
-keep class com.facebook.jni.** { *; }
-keep class com.facebook.soloader.** { *; }

# Keep all native methods (JNI entry points)
-keepclasseswithmembernames class * {
    native <methods>;
}

# Keep HybridData for fbjni
-keepclassmembers class * {
    com.facebook.jni.HybridData *;
}

# Suppress warnings for optional javax annotations that fbjni/soloader reference but don't need at runtime
-dontwarn javax.annotation.**
-dontwarn javax.annotation.concurrent.**
