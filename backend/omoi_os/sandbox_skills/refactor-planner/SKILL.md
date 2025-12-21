---
description: Plan safe refactoring with dependency analysis, impact assessment, and rollback strategies
globs: ["**/*.py", "**/*.ts", "**/*.tsx"]
---

# Refactor Planner

Plan safe, incremental refactoring with proper impact analysis.

## Refactoring Workflow

```
1. Analyze → 2. Plan → 3. Test → 4. Execute → 5. Verify
```

### 1. Analyze Current State
- Understand existing code structure
- Map dependencies (what uses this code)
- Identify coupling and cohesion issues
- Document current behavior with tests

### 2. Plan the Refactoring
- Define target state clearly
- Break into small, reversible steps
- Identify risk points
- Plan rollback strategy

### 3. Test Coverage First
- Ensure existing tests pass
- Add tests for uncovered behavior
- Create integration tests for dependencies
- **Never refactor without tests**

### 4. Execute Incrementally
- One logical change per commit
- Run tests after each step
- Keep the system working throughout
- Commit frequently

### 5. Verify Results
- All tests still pass
- No new warnings/errors
- Performance unchanged (or improved)
- Dependencies still work

## Refactoring Patterns

### Extract Function

**When**: Code block is reused or too complex

```python
# Before
def process_order(order):
    # Calculate total
    total = 0
    for item in order.items:
        price = item.price * item.quantity
        if item.discount:
            price *= (1 - item.discount)
        total += price
    # ... more code

# After
def calculate_item_price(item) -> float:
    """Calculate price for single item with discount."""
    price = item.price * item.quantity
    if item.discount:
        price *= (1 - item.discount)
    return price

def calculate_order_total(order) -> float:
    """Calculate total order price."""
    return sum(calculate_item_price(item) for item in order.items)

def process_order(order):
    total = calculate_order_total(order)
    # ... more code
```

### Extract Class

**When**: A class has too many responsibilities

```python
# Before: User class doing too much
class User:
    def authenticate(self, password): ...
    def send_email(self, subject, body): ...
    def generate_report(self): ...

# After: Split by responsibility
class User:
    def __init__(self):
        self.auth = UserAuthenticator(self)
        self.notifier = UserNotifier(self)
        self.reporter = UserReporter(self)

class UserAuthenticator:
    def authenticate(self, password): ...

class UserNotifier:
    def send_email(self, subject, body): ...

class UserReporter:
    def generate_report(self): ...
```

### Replace Conditional with Polymorphism

**When**: Type checks or switch statements

```python
# Before
def get_price(animal_type):
    if animal_type == "dog":
        return 50
    elif animal_type == "cat":
        return 30
    elif animal_type == "bird":
        return 20

# After
class Animal:
    def get_price(self) -> int:
        raise NotImplementedError

class Dog(Animal):
    def get_price(self) -> int:
        return 50

class Cat(Animal):
    def get_price(self) -> int:
        return 30

class Bird(Animal):
    def get_price(self) -> int:
        return 20
```

### Introduce Parameter Object

**When**: Function has too many parameters

```python
# Before
def create_user(name, email, phone, address, city, state, zip_code):
    ...

# After
@dataclass
class Address:
    street: str
    city: str
    state: str
    zip_code: str

@dataclass
class UserInfo:
    name: str
    email: str
    phone: str
    address: Address

def create_user(user_info: UserInfo):
    ...
```

## Dependency Analysis

### Finding Usages

```bash
# Find all usages of a function
grep -rn "function_name" --include="*.py" .

# Find imports of a module
grep -rn "from module import\|import module" --include="*.py" .

# Find class inheritance
grep -rn "class.*\(ClassName\)" --include="*.py" .
```

### Impact Assessment Template

```markdown
## Refactoring: {Description}

### Current State
- File(s): `path/to/file.py`
- Function/Class: `ClassName.method_name`
- Lines: ~{count}

### Target State
{Description of desired outcome}

### Dependencies (What uses this code)
- `module_a.py:42` - Direct call
- `module_b.py:88` - Imports class
- `tests/test_module.py` - Test coverage

### Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking API | Medium | High | Maintain old interface temporarily |
| Performance regression | Low | Medium | Benchmark before/after |

### Execution Plan
1. [ ] Add tests for current behavior
2. [ ] Create new structure alongside old
3. [ ] Migrate callers one by one
4. [ ] Remove old code
5. [ ] Run full test suite

### Rollback Plan
- Revert commit: `git revert {commit}`
- Or restore from: `git checkout {branch} -- {file}`
```

## Safe Refactoring Rules

1. **Make one change at a time** - Don't mix refactoring with features
2. **Keep tests passing** - If tests break, you've changed behavior
3. **Commit after each step** - Easy to rollback if needed
4. **Use IDE refactoring tools** - They update all references
5. **Review before push** - Check diff for unintended changes

## Refactoring Checklist

Before:
- [ ] Tests exist and pass
- [ ] Dependencies documented
- [ ] Plan approved

During:
- [ ] One change per commit
- [ ] Tests pass after each step
- [ ] No behavior changes

After:
- [ ] All tests pass
- [ ] No new warnings
- [ ] Documentation updated
- [ ] PR reviewed

## Tools

### Python
```bash
# Static analysis
pylint path/to/file.py
mypy path/to/file.py

# Find dead code
vulture path/to/

# Complexity analysis
radon cc path/to/ -a

# Automatic refactoring
rope-refactor
```

### TypeScript
```bash
# Static analysis
eslint src/
tsc --noEmit

# Find dead code
ts-prune

# Circular dependencies
madge --circular src/
```
