# Trust-tiered admission vs memory pollution (exploratory)

Stream of 400 tasks with 200 one-off notes tied to their module files; rare scenario; 3 repetitions.

| Arm | Needed rule injected | One-off notes injected / task | Learned notes archived | Active notes | Held-out pass@1 | C6 violated (H04, H07, H11) | Crashed |
|---|---|---|---|---|---|---|---|
| none | 44% | 4.1 | 0 | 208 | 36% | 4/9 | 0 |
| type_aware | 48% | 4.0 | 2 | 99 | 33% | 3/9 | 0 |
| tiered | 82% | 1.7 | 0 | 208 | 67% | 1/9 | 0 |
| tiered+type_aware | 82% | 1.7 | 2 | 99 | 76% | 0/9 | 0 |

Tiers of active notes at the end (rep 1):

- none: {'learned convention': 2, 'learned repeated': 4, 'learned policy': 2, 'learned candidate': 1, 'one-off candidate': 200}
- type_aware: {'learned convention': 2, 'learned repeated': 4, 'learned policy': 2, 'one-off candidate': 91}
- tiered: {'learned convention': 2, 'learned repeated': 4, 'learned policy': 2, 'learned candidate': 1, 'one-off candidate': 200}
- tiered+type_aware: {'learned convention': 2, 'learned repeated': 4, 'learned policy': 2, 'one-off candidate': 91}
