# Step Definition Templates

## pytest-bdd (Python)

```python
# conftest.py
from pytest_bdd import given, when, then, parsers
import pytest


# ── Given ──────────────────────────────────────────────────────────────────

@given(parsers.parse('手机号 "{phone}" 尚未注册'))
def phone_not_registered(phone, db):
    db.delete_user_if_exists(phone)


@given('系统处于正常运行状态')
def system_healthy(app):
    assert app.is_healthy()


# ── When ───────────────────────────────────────────────────────────────────

@when(parsers.parse('用户输入手机号 "{phone}" 和验证码 "{code}"'))
def input_phone_and_code(phone, code, page):
    page.fill("#phone-input", phone)
    page.fill("#code-input", code)


@when('用户点击"注册"按钮')
def click_register(page):
    page.click("#register-btn")


# ── Then ───────────────────────────────────────────────────────────────────

@then('系统创建新账号')
def account_created(db, phone):
    assert db.user_exists(phone)


@then(parsers.parse('页面显示"{message}"'))
def page_shows_message(message, page):
    assert page.locator(f"text={message}").is_visible()


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def db():
    # 返回数据库连接 / test client
    pass

@pytest.fixture
def page(playwright):
    browser = playwright.chromium.launch()
    yield browser.new_page()
    browser.close()
```

### conftest.py 中注册 feature 文件
```python
# test_registration.py
from pytest_bdd import scenarios

scenarios("features/registration.feature")
```

---

## Behave (Python)

```python
# features/steps/registration_steps.py
from behave import given, when, then
from hamcrest import assert_that, equal_to


@given('手机号 "{phone}" 尚未注册')
def step_phone_not_registered(context, phone):
    context.db.delete_user_if_exists(phone)


@when('用户提交注册信息')
def step_submit_registration(context):
    context.response = context.client.post("/register", json={
        "phone": context.phone,
        "code": context.code
    })


@then('系统创建新账号')
def step_account_created(context):
    assert_that(context.db.user_exists(context.phone), equal_to(True))


@then('页面显示"{message}"')
def step_page_shows(context, message):
    assert_that(context.response.json()["message"], equal_to(message))
```

---

## Cucumber (Java)

```java
// src/test/java/steps/RegistrationSteps.java
import io.cucumber.java.zh_cn.*;
import static org.assertj.core.api.Assertions.*;

public class RegistrationSteps {

    private UserService userService = new UserService();
    private String lastResponse;

    @假设("手机号 {string} 尚未注册")
    public void phoneNotRegistered(String phone) {
        userService.deleteIfExists(phone);
    }

    @当("用户提交注册信息")
    public void submitRegistration() {
        lastResponse = userService.register(phone, code);
    }

    @那么("系统创建新账号")
    public void accountCreated() {
        assertThat(userService.exists(phone)).isTrue();
    }

    @那么("页面显示{string}")
    public void pageShows(String message) {
        assertThat(lastResponse).contains(message);
    }
}
```

---

## Cucumber (JavaScript / TypeScript)

```typescript
// features/step_definitions/registration.steps.ts
import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from '@playwright/test';

Given('手机号 {string} 尚未注册', async function (phone: string) {
  await this.db.deleteUserIfExists(phone);
});

When('用户提交注册信息', async function () {
  await this.page.click('#register-btn');
});

Then('系统创建新账号', async function () {
  const exists = await this.db.userExists(this.phone);
  expect(exists).toBe(true);
});

Then('页面显示{string}', async function (message: string) {
  await expect(this.page.getByText(message)).toBeVisible();
});
```

---

## 生成原则

为 `.feature` 文件生成 Step 骨架时：

1. **提取所有唯一步骤** — 相同文本的步骤只生成一次
2. **识别参数** — `"..."` 中的内容转为函数参数
3. **分组** — Given / When / Then 各自分块
4. **加 `pass` / `// TODO`** — 保持骨架可运行
5. **输出文件名** — `steps/<feature_name>_steps.py`（或对应语言后缀）
