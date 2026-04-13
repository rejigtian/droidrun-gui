# Gradle Kotlin Multiplatform 插件冲突 - 快速修复

## 🚀 快速修复（3步）

### 步骤1: 检查插件声明位置

```bash
# 查找所有插件声明
grep -r "kotlin.multiplatform" . --include="*.gradle" --include="*.gradle.kts"
```

### 步骤2: 统一到 settings.gradle

**只在 `settings.gradle` 或 `settings.gradle.kts` 中声明版本：**

```groovy
// settings.gradle
pluginManagement {
    plugins {
        id 'org.jetbrains.kotlin.multiplatform' version '2.2.0'
    }
}
```

```kotlin
// settings.gradle.kts
pluginManagement {
    plugins {
        id("org.jetbrains.kotlin.multiplatform") version "2.2.0"
    }
}
```

### 步骤3: 移除 build.gradle 中的版本

**在所有 `build.gradle` 中只使用插件ID，不指定版本：**

```groovy
// build.gradle
plugins {
    id 'org.jetbrains.kotlin.multiplatform'  // 不指定版本
}
```

```kotlin
// build.gradle.kts
plugins {
    id("org.jetbrains.kotlin.multiplatform")  // 不指定版本
}
```

## 🔧 一键修复脚本

```bash
# 运行诊断脚本
./docs/guides/fix-gradle-plugin-conflict.sh
```

## 🧹 清理缓存

```bash
# 停止 Gradle 守护进程
./gradlew --stop

# 清理项目缓存
rm -rf .gradle build

# 清理所有子模块
find . -type d -name "build" -exec rm -rf {} +

# 重新同步
./gradlew clean
```

## ✅ 验证修复

```bash
# 检查插件解析
./gradlew tasks --all

# 清理构建
./gradlew clean
```

## 📋 检查清单

- [ ] 插件版本只在 `settings.gradle` 中声明
- [ ] 所有 `build.gradle` 中移除了版本号
- [ ] 已清理 Gradle 缓存
- [ ] 已清理项目构建目录
- [ ] 重新同步了项目

## 📖 详细文档

查看完整解决方案：[gradle-kotlin-multiplatform-plugin-fix.md](./gradle-kotlin-multiplatform-plugin-fix.md)

