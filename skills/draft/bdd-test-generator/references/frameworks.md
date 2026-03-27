# BDD 框架集成指南

## 目录
1. [Cucumber (Java / JS / Ruby)](#cucumber)
2. [Behave (Python)](#behave)
3. [SpecFlow (.NET)](#specflow)
4. [Playwright BDD](#playwright-bdd)
5. [通用最佳实践](#best-practices)

---

## Cucumber

### 目录结构
```
src/
└── test/
    ├── resources/features/   ← .feature 文件放这里
    │   └── login.feature
    └── java/steps/
        └── LoginSteps.java   ← Step Definitions
```

### 步骤定义示例（Java）
```java
@Given("用户已注册邮箱 {string}")
public void userHasRegisteredEmail(String email) {
    // 准备测试数据
}

@When("用户输入正确的邮箱和密码")
public void userEntersCorrectCredentials() {
    // 执行操作
}

@Then("系统跳转到主页")
public void systemRedirectsToHomePage() {
    // 断言
    assertEquals("/home", driver.getCurrentUrl());
}
```

### 运行命令
```bash
mvn test -Dcucumber.filter.tags="@smoke"
```

---

## Behave (Python)

### 目录结构
```
features/
├── login.feature
├── steps/
│   └── login_steps.py
└── environment.py    ← 钩子函数（Before/After）
```

### 步骤定义示例
```python
from behave import given, when, then

@given('用户已注册邮箱 "{email}"')
def step_user_registered(context, email):
    context.user = create_test_user(email)

@when('用户输入正确的邮箱和密码')
def step_user_enters_credentials(context):
    context.response = login(context.user.email, context.user.password)

@then('系统跳转到主页')
def step_redirect_to_home(context):
    assert context.response.url == '/home'
```

### 运行命令
```bash
behave --tags=@smoke
behave features/login.feature
```

---

## SpecFlow (.NET)

### NuGet 依赖
```xml
<PackageReference Include="SpecFlow" Version="3.*" />
<PackageReference Include="SpecFlow.NUnit" Version="3.*" />
```

### 步骤定义示例（C#）
```csharp
[Given(@"用户已注册邮箱 ""(.*)""")]
public void GivenUserHasRegisteredEmail(string email)
{
    _testUser = UserFactory.Create(email);
}

[When(@"用户输入正确的邮箱和密码")]
public void WhenUserEntersCorrectCredentials()
{
    _response = _authService.Login(_testUser.Email, _testUser.Password);
}

[Then(@"系统跳转到主页")]
public void ThenSystemRedirectsToHomePage()
{
    Assert.AreEqual("/home", _response.RedirectUrl);
}
```

---

## Playwright BDD

### 安装
```bash
npm install -D @cucumber/cucumber playwright
npx playwright install
```

### 目录结构
```
features/
├── login.feature
└── steps/
    └── login.steps.ts
```

### 步骤定义示例（TypeScript）
```typescript
import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from '@playwright/test';

Given('用户已注册邮箱 {string}', async function(email: string) {
  await this.page.goto('/register');
  // 创建测试用户...
});

When('用户输入正确的邮箱和密码', async function() {
  await this.page.fill('[name=email]', this.testUser.email);
  await this.page.fill('[name=password]', this.testUser.password);
  await this.page.click('[type=submit]');
});

Then('系统跳转到主页', async function() {
  await expect(this.page).toHaveURL('/home');
});
```

### 运行命令
```bash
npx cucumber-js --tags "@smoke"
```

---

## 通用最佳实践

### 测试数据管理
- 使用 `Background` 的 `Given` 步骤通过 API 或工厂方法创建数据，避免依赖 UI
- 每个场景独立，测试结束后清理数据（`After` 钩子）
- 敏感数据（密码、Token）存 `.env`，不写进 feature 文件

### 标签策略
```
# 持续集成只跑 smoke
@smoke    → CI/CD 必跑，< 5 分钟
@regression → 每日定时，< 30 分钟
@wip      → 本地开发，CI 跳过
```

### Scenario Outline 最佳实践
- Examples 表格保持 ≤ 10 行，超过则拆分场景
- 列名使用描述性词汇，不用 `input1`, `input2`
- 每行 Examples 代表一个独立的业务规则

### 步骤库复用
创建共享步骤定义文件（`common_steps`），存放跨 feature 的通用步骤：
- 登录/登出
- 导航到某页面  
- 等待加载完成
- 截图/日志记录
