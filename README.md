graph TD
    A[Main Script] --> B[Landing Zone Manager]
    B --> C[AWS Session Manager]
    C --> D[Resource Scanner]
    D --> E[Alarm Manager]
    E --> F[CloudWatch Alarm Definitions]
    F --> G[Alarm Deployment]