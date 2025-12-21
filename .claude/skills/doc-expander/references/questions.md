# Question Templates

Generate targeted research questions based on documentation type.

## Table of Contents

1. [Library Documentation](#library-documentation)
2. [API Documentation](#api-documentation)
3. [Framework Documentation](#framework-documentation)
4. [Tool/CLI Documentation](#toolcli-documentation)
5. [Expanding Existing Docs](#expanding-existing-docs)
6. [Domain-Specific Templates](#domain-specific-templates)

---

## Library Documentation

### Foundation Questions
```
- What is {library} and what problem does it solve?
- What are the core concepts and terminology?
- What are the key features and capabilities?
- How does {library} compare to alternatives like {alt1}, {alt2}?
- What is the license and maintenance status?
```

### Architecture Questions
```
- What is the high-level architecture of {library}?
- What are the main modules/packages and their responsibilities?
- How do the components interact with each other?
- What design patterns does {library} use?
- What are the extension points for customization?
```

### Usage Questions
```
- How do I install {library}?
- What are the system requirements and dependencies?
- What is the basic usage pattern / hello world example?
- What are the most common use cases?
- What configuration options are available?
```

### Integration Questions
```
- How does {library} integrate with {framework}?
- What are the required and optional dependencies?
- Are there official plugins, extensions, or adapters?
- How do I use {library} with {database/service}?
- What environment variables or config files does it use?
```

### Advanced Questions
```
- How do I handle {edge case scenario}?
- What are the performance characteristics and benchmarks?
- How do I optimize {library} for production?
- What security considerations should I be aware of?
- How do I debug issues with {library}?
```

### Migration Questions
```
- What changed between version {old} and {new}?
- How do I migrate from {old_library} to {library}?
- What are the breaking changes in the latest version?
- Are there migration guides or codemods available?
```

---

## API Documentation

### Endpoint Questions
```
- What endpoints are available in this API?
- What HTTP methods does each endpoint support?
- What are the required and optional parameters?
- What does the request body schema look like?
- What does the response schema look like?
```

### Authentication Questions
```
- What authentication methods are supported?
- How do I obtain API credentials?
- How do I refresh tokens?
- What are the rate limits?
- How are permissions/scopes structured?
```

### Error Handling Questions
```
- What error codes can be returned?
- What does each error code mean?
- How should I handle rate limiting?
- What is the retry strategy for failures?
- How do I get more details about errors?
```

### Integration Questions
```
- Are there official SDKs or client libraries?
- How do I handle pagination?
- How do I filter and sort results?
- What webhooks are available?
- How do I test in a sandbox environment?
```

---

## Framework Documentation

### Getting Started Questions
```
- How do I create a new {framework} project?
- What is the recommended project structure?
- What are the core concepts I need to understand?
- What is the development workflow?
- How do I run the development server?
```

### Routing Questions
```
- How does routing work in {framework}?
- How do I define dynamic routes?
- How do I handle nested routes?
- How do I implement middleware?
- How do I handle 404 and error pages?
```

### Data Questions
```
- How do I fetch data in {framework}?
- How do I manage state?
- How do I handle forms and validation?
- How do I connect to a database?
- How do I implement caching?
```

### Deployment Questions
```
- How do I build for production?
- What hosting options are recommended?
- How do I configure environment variables?
- How do I implement CI/CD?
- What are the performance optimization techniques?
```

---

## Tool/CLI Documentation

### Installation Questions
```
- How do I install {tool}?
- What are the system requirements?
- How do I verify the installation?
- How do I update to the latest version?
- How do I install specific versions?
```

### Command Questions
```
- What commands are available?
- What are the most commonly used commands?
- What flags and options does each command support?
- How do I get help for a specific command?
- Are there command aliases or shortcuts?
```

### Configuration Questions
```
- How do I configure {tool}?
- Where is the configuration file located?
- What configuration options are available?
- How do I set up project-specific configuration?
- How do I configure environment-specific settings?
```

### Workflow Questions
```
- What is the typical workflow for {use case}?
- How do I integrate {tool} with {other tool}?
- How do I automate common tasks?
- How do I troubleshoot common issues?
- What are the best practices for using {tool}?
```

---

## Expanding Existing Docs

When expanding existing documentation, analyze gaps with these questions:

### Coverage Analysis
```
- What topics are covered in the current documentation?
- What topics are mentioned but not explained?
- What common questions are not answered?
- What code examples are missing?
- What use cases are not addressed?
```

### Depth Analysis
```
- Which sections need more detail?
- Which concepts need better explanations?
- Which examples need more context?
- Which configurations need documentation?
- Which edge cases need coverage?
```

### Structure Analysis
```
- Is the documentation well-organized?
- Are there missing sections that should exist?
- Is there a clear progression from beginner to advanced?
- Are related topics linked together?
- Is there a troubleshooting section?
```

### Currency Analysis
```
- Is the documentation up to date?
- Are deprecated features still documented?
- Are new features documented?
- Are version-specific notes included?
- Are breaking changes documented?
```

---

## Domain-Specific Templates

### Database Library
```
- How do I connect to the database?
- How do I define models/schemas?
- How do I perform CRUD operations?
- How do I handle migrations?
- How do I optimize query performance?
- How do I handle transactions?
- How do I implement connection pooling?
```

### Authentication Library
```
- What authentication strategies are supported?
- How do I implement login/logout?
- How do I handle sessions vs tokens?
- How do I implement password reset?
- How do I implement social login?
- How do I handle refresh tokens?
- How do I implement role-based access?
```

### Testing Library
```
- How do I set up the testing environment?
- How do I write unit tests?
- How do I write integration tests?
- How do I mock dependencies?
- How do I generate test coverage?
- How do I run tests in parallel?
- How do I handle async tests?
```

### UI Component Library
```
- How do I install and set up the library?
- What components are available?
- How do I customize component styles?
- How do I handle theming?
- How do I implement responsive design?
- How do I handle accessibility?
- How do I integrate with forms?
```

### HTTP Client Library
```
- How do I make GET/POST/PUT/DELETE requests?
- How do I handle request headers?
- How do I send form data and file uploads?
- How do I handle response parsing?
- How do I implement interceptors?
- How do I handle timeouts and retries?
- How do I cancel requests?
```

---

## Question Generation Process

1. **Identify the documentation type** (library, API, framework, tool)
2. **Select relevant question templates** from above
3. **Customize questions** with specific library/tool names
4. **Prioritize questions** based on current doc gaps
5. **Research each question** using DeepWiki and Context7
6. **Synthesize findings** into structured documentation
