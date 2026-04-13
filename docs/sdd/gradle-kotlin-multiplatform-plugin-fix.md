# Gradle Kotlin Multiplatform 插件冲突解决方案

## 错误信息

```
Error resolving plugin [id: 'org.jetbrains.kotlin.multiplatform', version: '2.2.0']

> The request for this plugin could not be satisfied because the plugin is already on the classpath with an unknown version, so compatibility cannot be checked.
```

## 问题原因

这个错误通常发生在以下情况：

1. **插件在多个地方被声明**：在 `settings.gradle` 和 `build.gradle` 中都声明了插件
2. **版本冲突**：不同地方声明了不同版本
3. **插件被重复添加**：通过不同的方式（plugins {} 和 apply plugin）都添加了插件
4. **Gradle 缓存问题**：Gradle 缓存了旧版本的插件

## 解决方案

### 方案1: 统一插件声明位置（推荐）

**只在 `settings.gradle` 或 `settings.gradle.kts` 中声明插件版本**

#### settings.gradle (Groovy)

```groovy
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
    plugins {
        id 'org.jetbrains.kotlin.multiplatform' version '2.2.0'
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "YourProject"
include ':app'
```

#### settings.gradle.kts (Kotlin DSL)

```kotlin
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
    plugins {
        id("org.jetbrains.kotlin.multiplatform") version "2.2.0"
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "YourProject"
include(":app")
```

**然后在模块的 `build.gradle` 中只使用插件ID，不指定版本：**

#### build.gradle (Groovy)

```groovy
plugins {
    id 'org.jetbrains.kotlin.multiplatform'
    id 'com.android.library' // 或其他插件
}

kotlin {
    // 配置...
}
```

#### build.gradle.kts (Kotlin DSL)

```kotlin
plugins {
    id("org.jetbrains.kotlin.multiplatform")
    id("com.android.library") // 或其他插件
}

kotlin {
    // 配置...
}
```

### 方案2: 移除重复的插件声明

检查以下文件，确保插件只在一个地方声明：

1. **settings.gradle** / **settings.gradle.kts**
2. **build.gradle** / **build.gradle.kts**（根项目和所有子模块）
3. **gradle.properties**

**查找命令**：
```bash
# 查找所有包含 multiplatform 的文件
grep -r "kotlin.multiplatform" . --include="*.gradle" --include="*.gradle.kts"

# 查找所有包含 version 的插件声明
grep -r "version.*2.2.0" . --include="*.gradle" --include="*.gradle.kts"
```

### 方案3: 使用 buildscript 块（旧方式）

如果项目使用传统的 `buildscript` 方式，确保只在根 `build.gradle` 中声明：

#### 根 build.gradle

```groovy
buildscript {
    ext.kotlin_version = '2.2.0'
    repositories {
        google()
        mavenCentral()
    }
    dependencies {
        classpath "org.jetbrains.kotlin:kotlin-gradle-plugin:$kotlin_version"
        // 其他 classpath 依赖...
    }
}

allprojects {
    repositories {
        google()
        mavenCentral()
    }
}
```

#### 模块 build.gradle

```groovy
apply plugin: 'org.jetbrains.kotlin.multiplatform'

kotlin {
    // 配置...
}
```

**注意**：不要同时使用 `plugins {}` 块和 `apply plugin`，选择一种方式。

### 方案4: 清理 Gradle 缓存

```bash
# 清理项目构建缓存
./gradlew clean

# 清理 Gradle 守护进程
./gradlew --stop

# 删除 Gradle 缓存目录
rm -rf ~/.gradle/caches/

# 删除项目的 .gradle 目录
rm -rf .gradle/

# 重新同步项目
./gradlew --refresh-dependencies
```

### 方案5: 检查版本兼容性

确保所有 Kotlin 相关插件版本兼容：

```groovy
// settings.gradle 或 build.gradle
plugins {
    id 'org.jetbrains.kotlin.multiplatform' version '2.2.0'
    id 'org.jetbrains.kotlin.android' version '2.2.0' // 版本必须一致
    id 'org.jetbrains.kotlin.jvm' version '2.2.0' // 版本必须一致
}
```

### 方案6: 使用版本目录（Version Catalog）

创建 `gradle/libs.versions.toml`：

```toml
[versions]
kotlin = "2.2.0"

[plugins]
kotlin-multiplatform = { id = "org.jetbrains.kotlin.multiplatform", version.ref = "kotlin" }
kotlin-android = { id = "org.jetbrains.kotlin.android", version.ref = "kotlin" }
```

然后在 `build.gradle.kts` 中使用：

```kotlin
plugins {
    alias(libs.plugins.kotlin.multiplatform)
    alias(libs.plugins.kotlin.android)
}
```

## 完整示例配置

### 推荐的目录结构

```
project/
├── settings.gradle.kts          # 只在这里声明插件版本
├── build.gradle.kts             # 根构建脚本
├── gradle.properties
├── gradle/
│   └── libs.versions.toml       # 版本目录（可选）
└── app/
    └── build.gradle.kts         # 只使用插件ID，不指定版本
```

### settings.gradle.kts（完整示例）

```kotlin
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
    plugins {
        id("org.jetbrains.kotlin.multiplatform") version "2.2.0"
        id("com.android.application") version "8.3.0"
        id("com.android.library") version "8.3.0"
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "MyKotlinMultiplatformApp"
include(":app")
```

### app/build.gradle.kts（完整示例）

```kotlin
plugins {
    id("org.jetbrains.kotlin.multiplatform")
    id("com.android.library")
}

android {
    namespace = "com.example.app"
    compileSdk = 34

    defaultConfig {
        minSdk = 24
    }
}

kotlin {
    androidTarget {
        compilations.all {
            kotlinOptions {
                jvmTarget = "1.8"
            }
        }
    }
    
    iosX64()
    iosArm64()
    iosSimulatorArm64()

    sourceSets {
        val commonMain by getting {
            dependencies {
                // 依赖...
            }
        }
        val androidMain by getting {
            dependencies {
                // Android 特定依赖...
            }
        }
    }
}
```

## 验证修复

修复后，运行以下命令验证：

```bash
# 清理并重新构建
./gradlew clean

# 检查插件解析
./gradlew tasks --all

# 同步项目（在 IDE 中）
# Android Studio: File > Sync Project with Gradle Files
```

## 常见错误和解决方案

### 错误1: 插件版本不匹配

**错误信息**：
```
Plugin [id: 'org.jetbrains.kotlin.multiplatform'] was not found
```

**解决方案**：确保在 `settings.gradle` 中正确声明了插件版本。

### 错误2: 仍然提示版本冲突

**解决方案**：
1. 删除所有 `build.gradle` 中的版本号
2. 只在 `settings.gradle` 中保留版本
3. 清理 Gradle 缓存

### 错误3: 子模块无法找到插件

**解决方案**：确保在根 `settings.gradle` 中包含了所有子模块：
```groovy
include ':app', ':shared', ':other-module'
```

## 最佳实践

1. **统一版本管理**：使用 `settings.gradle` 或版本目录统一管理插件版本
2. **避免重复声明**：插件版本只在一个地方声明
3. **使用版本目录**：对于大型项目，使用 `libs.versions.toml` 管理版本
4. **定期更新**：保持 Kotlin 和 Gradle 插件版本同步更新
5. **清理缓存**：遇到问题时先清理 Gradle 缓存

## 参考资源

- [Kotlin Multiplatform 官方文档](https://kotlinlang.org/docs/multiplatform.html)
- [Gradle 插件管理文档](https://docs.gradle.org/current/userguide/plugins.html)
- [Gradle 版本目录文档](https://docs.gradle.org/current/userguide/platforms.html)

## 更新日志

- 2024-XX-XX: 初始版本，解决 Kotlin Multiplatform 插件冲突问题

