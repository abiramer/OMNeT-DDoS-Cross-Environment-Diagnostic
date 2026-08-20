# Canonical run5 aggregate results

Only run5 is canonical, and only aggregate, non-row-level evidence is reported here. The canonical design
uses ten independent source-group-aware CICDDoS2019 splits and ten independent
simulation seeds per scenario (40 simulations total). No favorable training
seed was selected. Run4 is excluded.

For [0,1]-bounded metrics, only displayed t-interval endpoints are constrained
to [0,1]; raw endpoints remain in the CSV. Undefined metrics are `not
estimable`. Paired differences and kappa/MCC intervals are not silently clipped.

## Main hold-out comparison

Aggregation: mean ± sample SD and two-sided 95% t CI across n=10 independent source-group-aware splits for every feature-set/classifier row.

| Features | Classifier | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC DDoS | Balanced accuracy | MCC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | xgboost | 0.9849 ± 0.0001 (95% CI 0.9848–0.9850) | 0.9773 ± 0.0006 (95% CI 0.9768–0.9777) | 0.9930 ± 0.0009 (95% CI 0.9923–0.9936) | 0.9851 ± 0.0002 (95% CI 0.9849–0.9852) | 0.9992 ± 0.0000 (95% CI 0.9992–0.9992) | 0.9992 ± 0.0000 (95% CI 0.9992–0.9992) | 0.9849 ± 0.0001 (95% CI 0.9848–0.9849) | 0.9699 ± 0.0002 (95% CI 0.9698–0.9701) |
| 4 | rf | 0.9836 ± 0.0010 (95% CI 0.9829–0.9844) | 0.9759 ± 0.0005 (95% CI 0.9756–0.9762) | 0.9918 ± 0.0022 (95% CI 0.9902–0.9934) | 0.9838 ± 0.0011 (95% CI 0.9830–0.9846) | 0.9990 ± 0.0001 (95% CI 0.9990–0.9991) | 0.9990 ± 0.0001 (95% CI 0.9990–0.9991) | 0.9836 ± 0.0010 (95% CI 0.9829–0.9843) | 0.9674 ± 0.0021 (95% CI 0.9659–0.9689) |
| 4 | mlp | 0.9273 ± 0.0084 (95% CI 0.9214–0.9333) | 0.9214 ± 0.0084 (95% CI 0.9153–0.9274) | 0.9348 ± 0.0124 (95% CI 0.9259–0.9437) | 0.9280 ± 0.0085 (95% CI 0.9219–0.9341) | 0.9753 ± 0.0129 (95% CI 0.9660–0.9845) | 0.9808 ± 0.0065 (95% CI 0.9761–0.9855) | 0.9273 ± 0.0083 (95% CI 0.9214–0.9333) | 0.8549 ± 0.0168 (95% CI 0.8428–0.8669) |
| 4 | hybrid | 0.9850 ± 0.0005 (95% CI 0.9846–0.9854) | 0.9763 ± 0.0007 (95% CI 0.9758–0.9768) | 0.9942 ± 0.0015 (95% CI 0.9931–0.9953) | 0.9852 ± 0.0006 (95% CI 0.9847–0.9856) | 0.9985 ± 0.0005 (95% CI 0.9981–0.9988) | 0.9984 ± 0.0004 (95% CI 0.9981–0.9987) | 0.9850 ± 0.0005 (95% CI 0.9846–0.9853) | 0.9701 ± 0.0011 (95% CI 0.9694–0.9709) |
| 6 | xgboost | 0.9865 ± 0.0011 (95% CI 0.9857–0.9873) | 0.9786 ± 0.0005 (95% CI 0.9782–0.9790) | 0.9948 ± 0.0028 (95% CI 0.9928–0.9968) | 0.9867 ± 0.0011 (95% CI 0.9858–0.9875) | 0.9993 ± 0.0001 (95% CI 0.9992–0.9994) | 0.9993 ± 0.0001 (95% CI 0.9993–0.9994) | 0.9865 ± 0.0011 (95% CI 0.9857–0.9873) | 0.9732 ± 0.0023 (95% CI 0.9716–0.9748) |
| 6 | rf | 0.9865 ± 0.0012 (95% CI 0.9857–0.9873) | 0.9796 ± 0.0007 (95% CI 0.9791–0.9801) | 0.9937 ± 0.0031 (95% CI 0.9915–0.9960) | 0.9866 ± 0.0012 (95% CI 0.9858–0.9875) | 0.9993 ± 0.0001 (95% CI 0.9992–0.9994) | 0.9993 ± 0.0001 (95% CI 0.9993–0.9994) | 0.9865 ± 0.0011 (95% CI 0.9857–0.9873) | 0.9731 ± 0.0024 (95% CI 0.9714–0.9748) |
| 6 | mlp | 0.9826 ± 0.0057 (95% CI 0.9784–0.9867) | 0.9750 ± 0.0069 (95% CI 0.9700–0.9799) | 0.9907 ± 0.0100 (95% CI 0.9835–0.9979) | 0.9827 ± 0.0058 (95% CI 0.9786–0.9869) | 0.9966 ± 0.0047 (95% CI 0.9932–0.9999) | 0.9972 ± 0.0026 (95% CI 0.9953–0.9990) | 0.9825 ± 0.0058 (95% CI 0.9784–0.9866) | 0.9653 ± 0.0115 (95% CI 0.9571–0.9736) |
| 6 | hybrid | 0.9866 ± 0.0012 (95% CI 0.9857–0.9874) | 0.9790 ± 0.0005 (95% CI 0.9786–0.9793) | 0.9945 ± 0.0030 (95% CI 0.9924–0.9967) | 0.9867 ± 0.0013 (95% CI 0.9858–0.9876) | 0.9991 ± 0.0005 (95% CI 0.9988–0.9995) | 0.9992 ± 0.0003 (95% CI 0.9989–0.9994) | 0.9865 ± 0.0012 (95% CI 0.9857–0.9874) | 0.9733 ± 0.0025 (95% CI 0.9715–0.9750) |
| 8 | xgboost | 0.9861 ± 0.0011 (95% CI 0.9853–0.9869) | 0.9785 ± 0.0012 (95% CI 0.9776–0.9793) | 0.9941 ± 0.0035 (95% CI 0.9916–0.9966) | 0.9862 ± 0.0011 (95% CI 0.9854–0.9870) | 0.9993 ± 0.0002 (95% CI 0.9992–0.9995) | 0.9993 ± 0.0001 (95% CI 0.9992–0.9994) | 0.9861 ± 0.0010 (95% CI 0.9853–0.9868) | 0.9723 ± 0.0022 (95% CI 0.9708–0.9739) |
| 8 | rf | 0.9867 ± 0.0010 (95% CI 0.9860–0.9874) | 0.9797 ± 0.0011 (95% CI 0.9789–0.9806) | 0.9940 ± 0.0034 (95% CI 0.9916–0.9964) | 0.9868 ± 0.0011 (95% CI 0.9860–0.9876) | 0.9993 ± 0.0002 (95% CI 0.9991–0.9995) | 0.9993 ± 0.0002 (95% CI 0.9992–0.9995) | 0.9867 ± 0.0010 (95% CI 0.9859–0.9874) | 0.9735 ± 0.0021 (95% CI 0.9720–0.9750) |
| 8 | mlp | 0.9836 ± 0.0059 (95% CI 0.9794–0.9878) | 0.9753 ± 0.0066 (95% CI 0.9706–0.9800) | 0.9924 ± 0.0069 (95% CI 0.9875–0.9973) | 0.9838 ± 0.0058 (95% CI 0.9796–0.9880) | 0.9974 ± 0.0020 (95% CI 0.9960–0.9988) | 0.9974 ± 0.0016 (95% CI 0.9963–0.9986) | 0.9836 ± 0.0059 (95% CI 0.9794–0.9877) | 0.9674 ± 0.0117 (95% CI 0.9590–0.9757) |
| 8 | hybrid | 0.9862 ± 0.0011 (95% CI 0.9854–0.9870) | 0.9788 ± 0.0011 (95% CI 0.9780–0.9796) | 0.9940 ± 0.0034 (95% CI 0.9916–0.9965) | 0.9864 ± 0.0011 (95% CI 0.9855–0.9872) | 0.9991 ± 0.0005 (95% CI 0.9988–0.9995) | 0.9992 ± 0.0004 (95% CI 0.9989–0.9995) | 0.9862 ± 0.0011 (95% CI 0.9854–0.9870) | 0.9726 ± 0.0022 (95% CI 0.9710–0.9742) |

## OMNeT++ cross-environment results by scenario

Aggregation: n=10 canonical simulation seeds per scenario. Within each simulation seed, each metric is first averaged across all n=10 trained-seed models; the displayed mean, SD, and 95% t CI are then calculated across the 10 simulation seeds. `Unique flows` counts each canonical flow once and is not multiplied by training seeds. Undefined single-class metrics remain `not estimable`.

| Features | Classifier | Scenario | Simulation seeds | Training seeds/model | Unique flows | BENIGN | DDoS | Predicted DDoS proportion | Accuracy | F1 | Balanced accuracy | MCC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | xgboost | DNSAmplification | 10 | 10 | 600 | 500 | 100 | 0.1667 ± 0.0000 (95% CI 0.1667–0.1667) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) |
| 4 | xgboost | Normal | 10 | 10 | 500 | 500 | 0 | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | not estimable | not estimable | not estimable |
| 4 | xgboost | SYNFlood | 10 | 10 | 8500 | 500 | 8000 | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 0.0588 ± 0.0000 (95% CI 0.0588–0.0588) | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 0.5000 ± 0.0000 (95% CI 0.5000–0.5000) | not estimable |
| 4 | xgboost | UDPFlood | 10 | 10 | 712 | 512 | 200 | 0.2810 ± 0.0067 (95% CI 0.2762–0.2859) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) |
| 4 | rf | DNSAmplification | 10 | 10 | 600 | 500 | 100 | 0.1667 ± 0.0000 (95% CI 0.1667–0.1667) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) |
| 4 | rf | Normal | 10 | 10 | 500 | 500 | 0 | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | not estimable | not estimable | not estimable |
| 4 | rf | SYNFlood | 10 | 10 | 8500 | 500 | 8000 | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 0.0588 ± 0.0000 (95% CI 0.0588–0.0588) | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 0.5000 ± 0.0000 (95% CI 0.5000–0.5000) | not estimable |
| 4 | rf | UDPFlood | 10 | 10 | 712 | 512 | 200 | 0.2844 ± 0.0029 (95% CI 0.2824–0.2865) | 0.9966 ± 0.0062 (95% CI 0.9922–1.0000) | 0.9939 ± 0.0112 (95% CI 0.9859–1.0000) | 0.9977 ± 0.0042 (95% CI 0.9946–1.0000) | 0.9917 ± 0.0152 (95% CI 0.9809–1.0026) |
| 4 | mlp | DNSAmplification | 10 | 10 | 600 | 500 | 100 | 0.0833 ± 0.0000 (95% CI 0.0833–0.0833) | 0.9167 ± 0.0000 (95% CI 0.9167–0.9167) | 0.5000 ± 0.0000 (95% CI 0.5000–0.5000) | 0.7500 ± 0.0000 (95% CI 0.7500–0.7500) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) |
| 4 | mlp | Normal | 10 | 10 | 500 | 500 | 0 | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | not estimable | not estimable | not estimable |
| 4 | mlp | SYNFlood | 10 | 10 | 8500 | 500 | 8000 | 0.0008 ± 0.0005 (95% CI 0.0004–0.0011) | 0.0596 ± 0.0005 (95% CI 0.0592–0.0600) | 0.0016 ± 0.0011 (95% CI 0.0009–0.0024) | 0.5004 ± 0.0003 (95% CI 0.5002–0.5006) | 0.0130 ± 0.0035 (95% CI 0.0105–0.0155) |
| 4 | mlp | UDPFlood | 10 | 10 | 712 | 512 | 200 | 0.1522 ± 0.0132 (95% CI 0.1428–0.1617) | 0.8478 ± 0.0132 (95% CI 0.8383–0.8572) | 0.4918 ± 0.0118 (95% CI 0.4834–0.5003) | 0.7419 ± 0.0113 (95% CI 0.7338–0.7501) | 0.7659 ± 0.3024 (95% CI 0.5496–0.9823) |
| 4 | hybrid | DNSAmplification | 10 | 10 | 600 | 500 | 100 | 0.1667 ± 0.0000 (95% CI 0.1667–0.1667) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) |
| 4 | hybrid | Normal | 10 | 10 | 500 | 500 | 0 | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | not estimable | not estimable | not estimable |
| 4 | hybrid | SYNFlood | 10 | 10 | 8500 | 500 | 8000 | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 0.0588 ± 0.0000 (95% CI 0.0588–0.0588) | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 0.5000 ± 0.0000 (95% CI 0.5000–0.5000) | not estimable |
| 4 | hybrid | UDPFlood | 10 | 10 | 712 | 512 | 200 | 0.2836 ± 0.0033 (95% CI 0.2813–0.2860) | 0.9974 ± 0.0048 (95% CI 0.9940–1.0000) | 0.9954 ± 0.0086 (95% CI 0.9892–1.0000) | 0.9982 ± 0.0033 (95% CI 0.9959–1.0000) | 0.9937 ± 0.0117 (95% CI 0.9853–1.0021) |
| 6 | xgboost | DNSAmplification | 10 | 10 | 600 | 500 | 100 | 0.1667 ± 0.0000 (95% CI 0.1667–0.1667) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) |
| 6 | xgboost | Normal | 10 | 10 | 500 | 500 | 0 | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | not estimable | not estimable | not estimable |
| 6 | xgboost | SYNFlood | 10 | 10 | 8500 | 500 | 8000 | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 0.0588 ± 0.0000 (95% CI 0.0588–0.0588) | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 0.5000 ± 0.0000 (95% CI 0.5000–0.5000) | not estimable |
| 6 | xgboost | UDPFlood | 10 | 10 | 712 | 512 | 200 | 0.2823 ± 0.0051 (95% CI 0.2786–0.2859) | 0.9988 ± 0.0020 (95% CI 0.9974–1.0000) | 0.9978 ± 0.0035 (95% CI 0.9953–1.0000) | 0.9992 ± 0.0013 (95% CI 0.9982–1.0000) | 0.9970 ± 0.0047 (95% CI 0.9937–1.0004) |
| 6 | rf | DNSAmplification | 10 | 10 | 600 | 500 | 100 | 0.1667 ± 0.0000 (95% CI 0.1667–0.1667) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) |
| 6 | rf | Normal | 10 | 10 | 500 | 500 | 0 | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | not estimable | not estimable | not estimable |
| 6 | rf | SYNFlood | 10 | 10 | 8500 | 500 | 8000 | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 0.0588 ± 0.0000 (95% CI 0.0588–0.0588) | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 0.5000 ± 0.0000 (95% CI 0.5000–0.5000) | not estimable |
| 6 | rf | UDPFlood | 10 | 10 | 712 | 512 | 200 | 0.2832 ± 0.0036 (95% CI 0.2806–0.2858) | 0.9978 ± 0.0046 (95% CI 0.9946–1.0000) | 0.9961 ± 0.0083 (95% CI 0.9902–1.0000) | 0.9985 ± 0.0031 (95% CI 0.9963–1.0000) | 0.9947 ± 0.0113 (95% CI 0.9866–1.0028) |
| 6 | mlp | DNSAmplification | 10 | 10 | 600 | 500 | 100 | 0.0005 ± 0.0008 (95% CI 0.0000–0.0011) | 0.8328 ± 0.0008 (95% CI 0.8323–0.8334) | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 0.4997 ± 0.0005 (95% CI 0.4994–0.5000) | -0.0582 ± 0.0000 (95% CI -0.0582–-0.0582) |
| 6 | mlp | Normal | 10 | 10 | 500 | 500 | 0 | 0.0006 ± 0.0010 (95% CI 0.0000–0.0013) | 0.9994 ± 0.0010 (95% CI 0.9987–1.0000) | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | not estimable | not estimable |
| 6 | mlp | SYNFlood | 10 | 10 | 8500 | 500 | 8000 | 0.0947 ± 0.0003 (95% CI 0.0945–0.0949) | 0.1535 ± 0.0003 (95% CI 0.1533–0.1537) | 0.1346 ± 0.0005 (95% CI 0.1343–0.1350) | 0.5500 ± 0.0007 (95% CI 0.5495–0.5505) | 0.1276 ± 0.0305 (95% CI 0.1058–0.1494) |
| 6 | mlp | UDPFlood | 10 | 10 | 712 | 512 | 200 | 0.0342 ± 0.0086 (95% CI 0.0280–0.0404) | 0.7409 ± 0.0035 (95% CI 0.7384–0.7435) | 0.0998 ± 0.0008 (95% CI 0.0992–0.1003) | 0.5458 ± 0.0064 (95% CI 0.5412–0.5504) | 0.6311 ± 0.4775 (95% CI 0.2895–0.9727) |
| 6 | hybrid | DNSAmplification | 10 | 10 | 600 | 500 | 100 | 0.1667 ± 0.0000 (95% CI 0.1667–0.1667) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) |
| 6 | hybrid | Normal | 10 | 10 | 500 | 500 | 0 | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | not estimable | not estimable | not estimable |
| 6 | hybrid | SYNFlood | 10 | 10 | 8500 | 500 | 8000 | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 0.0588 ± 0.0000 (95% CI 0.0588–0.0588) | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 0.5000 ± 0.0000 (95% CI 0.5000–0.5000) | not estimable |
| 6 | hybrid | UDPFlood | 10 | 10 | 712 | 512 | 200 | 0.2835 ± 0.0030 (95% CI 0.2814–0.2856) | 0.9976 ± 0.0043 (95% CI 0.9945–1.0000) | 0.9956 ± 0.0078 (95% CI 0.9901–1.0000) | 0.9983 ± 0.0029 (95% CI 0.9962–1.0000) | 0.9941 ± 0.0105 (95% CI 0.9865–1.0016) |
| 8 | xgboost | DNSAmplification | 10 | 10 | 600 | 500 | 100 | 0.1667 ± 0.0000 (95% CI 0.1667–0.1667) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) |
| 8 | xgboost | Normal | 10 | 10 | 500 | 500 | 0 | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | not estimable | not estimable | not estimable |
| 8 | xgboost | SYNFlood | 10 | 10 | 8500 | 500 | 8000 | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 0.0588 ± 0.0000 (95% CI 0.0588–0.0588) | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 0.5000 ± 0.0000 (95% CI 0.5000–0.5000) | not estimable |
| 8 | xgboost | UDPFlood | 10 | 10 | 712 | 512 | 200 | 0.2820 ± 0.0052 (95% CI 0.2783–0.2857) | 0.9991 ± 0.0017 (95% CI 0.9979–1.0000) | 0.9984 ± 0.0029 (95% CI 0.9963–1.0000) | 0.9993 ± 0.0011 (95% CI 0.9985–1.0000) | 0.9978 ± 0.0038 (95% CI 0.9951–1.0005) |
| 8 | rf | DNSAmplification | 10 | 10 | 600 | 500 | 100 | 0.1423 ± 0.0024 (95% CI 0.1406–0.1440) | 0.9757 ± 0.0024 (95% CI 0.9740–0.9774) | 0.8697 ± 0.0128 (95% CI 0.8606–0.8789) | 0.9270 ± 0.0071 (95% CI 0.9219–0.9321) | 0.9667 ± 0.0117 (95% CI 0.9583–0.9751) |
| 8 | rf | Normal | 10 | 10 | 500 | 500 | 0 | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | not estimable | not estimable | not estimable |
| 8 | rf | SYNFlood | 10 | 10 | 8500 | 500 | 8000 | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 0.0588 ± 0.0000 (95% CI 0.0588–0.0588) | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 0.5000 ± 0.0000 (95% CI 0.5000–0.5000) | not estimable |
| 8 | rf | UDPFlood | 10 | 10 | 712 | 512 | 200 | 0.2649 ± 0.0044 (95% CI 0.2617–0.2680) | 0.9740 ± 0.0085 (95% CI 0.9679–0.9801) | 0.9309 ± 0.0183 (95% CI 0.9178–0.9440) | 0.9591 ± 0.0074 (95% CI 0.9539–0.9644) | 0.9310 ± 0.0233 (95% CI 0.9144–0.9477) |
| 8 | mlp | DNSAmplification | 10 | 10 | 600 | 500 | 100 | 0.2670 ± 0.0046 (95% CI 0.2637–0.2703) | 0.7997 ± 0.0046 (95% CI 0.7964–0.8030) | 0.5619 ± 0.0016 (95% CI 0.5607–0.5630) | 0.7598 ± 0.0028 (95% CI 0.7578–0.7618) | 0.8661 ± 0.0056 (95% CI 0.8621–0.8701) |
| 8 | mlp | Normal | 10 | 10 | 500 | 500 | 0 | 0.1800 ± 0.0040 (95% CI 0.1771–0.1829) | 0.8200 ± 0.0040 (95% CI 0.8171–0.8229) | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | not estimable | not estimable |
| 8 | mlp | SYNFlood | 10 | 10 | 8500 | 500 | 8000 | 0.0105 ± 0.0003 (95% CI 0.0103–0.0107) | 0.0484 ± 0.0003 (95% CI 0.0482–0.0486) | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 0.4111 ± 0.0025 (95% CI 0.4093–0.4129) | -0.9378 ± 0.0147 (95% CI -0.9483–-0.9273) |
| 8 | mlp | UDPFlood | 10 | 10 | 712 | 512 | 200 | 0.2712 ± 0.0012 (95% CI 0.2703–0.2721) | 0.8398 ± 0.0034 (95% CI 0.8374–0.8422) | 0.6369 ± 0.0090 (95% CI 0.6305–0.6434) | 0.7965 ± 0.0035 (95% CI 0.7940–0.7990) | 0.9843 ± 0.0183 (95% CI 0.9713–0.9974) |
| 8 | hybrid | DNSAmplification | 10 | 10 | 600 | 500 | 100 | 0.1662 ± 0.0008 (95% CI 0.1656–0.1667) | 0.9995 ± 0.0008 (95% CI 0.9989–1.0000) | 0.9984 ± 0.0025 (95% CI 0.9966–1.0000) | 0.9985 ± 0.0024 (95% CI 0.9968–1.0000) | 0.9982 ± 0.0029 (95% CI 0.9961–1.0003) |
| 8 | hybrid | Normal | 10 | 10 | 500 | 500 | 0 | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 1.0000 ± 0.0000 (95% CI 1.0000–1.0000) | not estimable | not estimable | not estimable |
| 8 | hybrid | SYNFlood | 10 | 10 | 8500 | 500 | 8000 | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 0.0588 ± 0.0000 (95% CI 0.0588–0.0588) | 0.0000 ± 0.0000 (95% CI 0.0000–0.0000) | 0.5000 ± 0.0000 (95% CI 0.5000–0.5000) | not estimable |
| 8 | hybrid | UDPFlood | 10 | 10 | 712 | 512 | 200 | 0.2832 ± 0.0043 (95% CI 0.2801–0.2863) | 0.9978 ± 0.0039 (95% CI 0.9951–1.0000) | 0.9961 ± 0.0068 (95% CI 0.9912–1.0000) | 0.9985 ± 0.0027 (95% CI 0.9966–1.0000) | 0.9947 ± 0.0093 (95% CI 0.9881–1.0014) |

## Feature sensitivity

Each row compares the same n=10 seed splits. Differences are left minus right; difference intervals are unbounded and therefore are not clipped. Holm p values come from the complete 270-comparison family.

| Stratum | Metric | Left | Right | Matched seeds | Mean difference (left−right) | Holm-adjusted p | Significant after Holm |
| --- | --- | --- | --- | --- | --- | --- | --- |
| hybrid | accuracy | 4 | 6 | 10 | -0.00158 (95% CI -0.00245–-0.00071) | 0.4033 | False |
| hybrid | f1 | 4 | 6 | 10 | -0.00154 (95% CI -0.00242–-0.00067) | 0.4611 | False |
| hybrid | accuracy | 4 | 8 | 10 | -0.00124 (95% CI -0.00202–-0.00045) | 0.7988 | False |
| hybrid | f1 | 4 | 8 | 10 | -0.00120 (95% CI -0.00200–-0.00040) | 0.9743 | False |
| hybrid | accuracy | 6 | 8 | 10 | 0.00034 (95% CI 0.00019–0.00050) | 0.1346 | False |
| hybrid | f1 | 6 | 8 | 10 | 0.00034 (95% CI 0.00019–0.00049) | 0.1091 | False |
| mlp | accuracy | 4 | 6 | 10 | -0.05521 (95% CI -0.06119–-0.04923) | 1.517e-06 | True |
| mlp | f1 | 4 | 6 | 10 | -0.05473 (95% CI -0.06088–-0.04858) | 2.085e-06 | True |
| mlp | accuracy | 4 | 8 | 10 | -0.05624 (95% CI -0.06057–-0.05192) | 7.95e-08 | True |
| mlp | f1 | 4 | 8 | 10 | -0.05578 (95% CI -0.06033–-0.05123) | 1.333e-07 | True |
| mlp | accuracy | 6 | 8 | 10 | -0.00103 (95% CI -0.00536–0.00330) | 1 | False |
| mlp | f1 | 6 | 8 | 10 | -0.00105 (95% CI -0.00535–0.00326) | 1 | False |
| rf | accuracy | 4 | 6 | 10 | -0.00286 (95% CI -0.00387–-0.00185) | 0.02407 | True |
| rf | f1 | 4 | 6 | 10 | -0.00283 (95% CI -0.00386–-0.00179) | 0.02995 | True |
| rf | accuracy | 4 | 8 | 10 | -0.00307 (95% CI -0.00402–-0.00212) | 0.00916 | True |
| rf | f1 | 4 | 8 | 10 | -0.00303 (95% CI -0.00401–-0.00206) | 0.01198 | True |
| rf | accuracy | 6 | 8 | 10 | -0.00021 (95% CI -0.00031–-0.00010) | 0.2275 | False |
| rf | f1 | 6 | 8 | 10 | -0.00021 (95% CI -0.00031–-0.00011) | 0.1906 | False |
| xgboost | accuracy | 4 | 6 | 10 | -0.00161 (95% CI -0.00235–-0.00088) | 0.126 | False |
| xgboost | f1 | 4 | 6 | 10 | -0.00160 (95% CI -0.00233–-0.00087) | 0.1315 | False |
| xgboost | accuracy | 4 | 8 | 10 | -0.00119 (95% CI -0.00190–-0.00049) | 0.5847 | False |
| xgboost | f1 | 4 | 8 | 10 | -0.00118 (95% CI -0.00189–-0.00046) | 0.6349 | False |
| xgboost | accuracy | 6 | 8 | 10 | 0.00042 (95% CI 0.00036–0.00048) | 1.706e-05 | True |
| xgboost | f1 | 6 | 8 | 10 | 0.00042 (95% CI 0.00037–0.00047) | 6.661e-06 | True |

## Principal feature-8 classifier comparisons

Each row uses n=10 matched seed splits. Holm p values come from the complete 270-comparison family.

| Stratum | Metric | Left | Right | Matched seeds | Mean difference (left−right) | Holm-adjusted p | Significant after Holm |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | accuracy | hybrid | mlp | 10 | 0.00263 (95% CI -0.00099–0.00625) | 1 | False |
| 8 | f1 | hybrid | mlp | 10 | 0.00258 (95% CI -0.00102–0.00618) | 1 | False |
| 8 | accuracy | hybrid | rf | 10 | -0.00047 (95% CI -0.00055–-0.00039) | 9.822e-05 | True |
| 8 | f1 | hybrid | rf | 10 | -0.00046 (95% CI -0.00054–-0.00038) | 0.0001006 | True |
| 8 | accuracy | hybrid | xgboost | 10 | 0.00012 (95% CI 0.00006–0.00018) | 0.2848 | False |
| 8 | f1 | hybrid | xgboost | 10 | 0.00012 (95% CI 0.00005–0.00018) | 0.3274 | False |
| 8 | accuracy | mlp | rf | 10 | -0.00310 (95% CI -0.00677–0.00056) | 1 | False |
| 8 | f1 | mlp | rf | 10 | -0.00304 (95% CI -0.00669–0.00061) | 1 | False |
| 8 | accuracy | mlp | xgboost | 10 | -0.00251 (95% CI -0.00614–0.00112) | 1 | False |
| 8 | f1 | mlp | xgboost | 10 | -0.00247 (95% CI -0.00608–0.00115) | 1 | False |
| 8 | accuracy | rf | xgboost | 10 | 0.00059 (95% CI 0.00053–0.00065) | 7.817e-07 | True |
| 8 | f1 | rf | xgboost | 10 | 0.00057 (95% CI 0.00052–0.00063) | 6.209e-07 | True |

## Feature-8 OMNeT++ consensus confusion matrices

Aggregation: all 10,312 unique canonical run5 flows. For each classifier, the prediction is the majority across all n=10 training-seed models; a 5–5 tie is resolved by the mean score. No training seed is selected.

| Features | Classifier | Training-seed aggregation | Unique flows | BENIGN | DDoS | TN | FP | FN | TP |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | xgboost | majority consensus across 10 seeds; mean score breaks 5–5 ties | 10312 | 2012 | 8300 | 2012 | 0 | 8000 | 300 |
| 8 | rf | majority consensus across 10 seeds; mean score breaks 5–5 ties | 10312 | 2012 | 8300 | 2008 | 4 | 8000 | 300 |
| 8 | mlp | majority consensus across 10 seeds; mean score breaks 5–5 ties | 10312 | 2012 | 8300 | 2012 | 0 | 8000 | 300 |
| 8 | hybrid | majority consensus across 10 seeds; mean score breaks 5–5 ties | 10312 | 2012 | 8300 | 2012 | 0 | 8000 | 300 |

## OMNeT++ classifier agreement

Aggregation: agreement and Cohen's kappa are calculated on the same 10,312 canonical flows for each training seed, then summarized across n=10 training seeds.

| Features | Classifier A | Classifier B | Training seeds | Agreement | Cohen's kappa | Agreement with ensemble |
| --- | --- | --- | --- | --- | --- | --- |
| 4 | mlp | hybrid | 10 | 0.9842 ± 0.0159 (95% CI 0.9728–0.9956) | 0.4980 ± 0.5158 (95% CI 0.1290–0.8670) | yes |
| 4 | rf | hybrid | 10 | 0.9999 ± 0.0001 (95% CI 0.9999–1.0000) | 0.9990 ± 0.0022 (95% CI 0.9974–1.0005) | yes |
| 4 | rf | mlp | 10 | 0.9841 ± 0.0159 (95% CI 0.9727–0.9955) | 0.4970 ± 0.5147 (95% CI 0.1288–0.8652) | no |
| 4 | xgboost | hybrid | 10 | 0.9998 ± 0.0001 (95% CI 0.9997–0.9999) | 0.9968 ± 0.0017 (95% CI 0.9955–0.9980) | yes |
| 4 | xgboost | mlp | 10 | 0.9840 ± 0.0160 (95% CI 0.9726–0.9954) | 0.4902 ± 0.5208 (95% CI 0.1177–0.8628) | no |
| 4 | xgboost | rf | 10 | 0.9998 ± 0.0001 (95% CI 0.9997–0.9998) | 0.9957 ± 0.0014 (95% CI 0.9947–0.9968) | no |
| 6 | mlp | hybrid | 10 | 0.8944 ± 0.1591 (95% CI 0.7806–1.0000) | 0.0052 ± 0.0239 (95% CI -0.0119–0.0223) | yes |
| 6 | rf | hybrid | 10 | 0.9999 ± 0.0001 (95% CI 0.9998–1.0000) | 0.9983 ± 0.0016 (95% CI 0.9971–0.9994) | yes |
| 6 | rf | mlp | 10 | 0.8943 ± 0.1591 (95% CI 0.7805–1.0000) | 0.0027 ± 0.0242 (95% CI -0.0145–0.0200) | no |
| 6 | xgboost | hybrid | 10 | 0.9999 ± 0.0001 (95% CI 0.9998–1.0000) | 0.9981 ± 0.0015 (95% CI 0.9970–0.9992) | yes |
| 6 | xgboost | mlp | 10 | 0.8943 ± 0.1590 (95% CI 0.7806–1.0000) | -0.0007 ± 0.0230 (95% CI -0.0172–0.0158) | no |
| 6 | xgboost | rf | 10 | 0.9998 ± 0.0000 (95% CI 0.9998–0.9998) | 0.9964 ± 0.0005 (95% CI 0.9960–0.9968) | no |
| 8 | mlp | hybrid | 10 | 0.9601 ± 0.0649 (95% CI 0.9136–1.0000) | 0.5466 ± 0.4814 (95% CI 0.2022–0.8910) | yes |
| 8 | rf | hybrid | 10 | 0.9970 ± 0.0076 (95% CI 0.9915–1.0000) | 0.9168 ± 0.2258 (95% CI 0.7553–1.0783) | yes |
| 8 | rf | mlp | 10 | 0.9570 ± 0.0633 (95% CI 0.9117–1.0000) | 0.4650 ± 0.4484 (95% CI 0.1442–0.7858) | no |
| 8 | xgboost | hybrid | 10 | 0.9998 ± 0.0002 (95% CI 0.9996–0.9999) | 0.9962 ± 0.0035 (95% CI 0.9938–0.9987) | yes |
| 8 | xgboost | mlp | 10 | 0.9599 ± 0.0650 (95% CI 0.9134–1.0000) | 0.5450 ± 0.4808 (95% CI 0.2011–0.8890) | no |
| 8 | xgboost | rf | 10 | 0.9968 ± 0.0075 (95% CI 0.9914–1.0000) | 0.9130 ± 0.2244 (95% CI 0.7525–1.0736) | no |

## Matched McNemar summary for feature 8

Each classifier pair has 10 exact, seedwise McNemar tests on identical hold-out sample IDs. Holm adjustment was applied over the complete 660-test family. Unmatched observations are never tested.

| Features | Classifier A | Classifier B | Matched seedwise tests | Matched observations/test (min–max) | Total discordant predictions | Holm-significant tests | Median Holm-adjusted p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | hybrid | mlp | 10 | 43500–43964 | 3599 | 9 | 1.353e-19 |
| 8 | hybrid | rf | 10 | 43500–43964 | 299 | 6 | 0.01526 |
| 8 | hybrid | xgboost | 10 | 43500–43964 | 152 | 0 | 1 |
| 8 | mlp | rf | 10 | 43500–43964 | 3898 | 9 | 1.411e-23 |
| 8 | mlp | xgboost | 10 | 43500–43964 | 3751 | 9 | 1.876e-15 |
| 8 | rf | xgboost | 10 | 43500–43964 | 451 | 9 | 0.03175 |

Detailed seed-level outputs are indexed in the timestamped supplementary file.


## Figure 5 publication-freeze output

`figures/figure5/` contains the approved feature-8 matched ten-seed ROC
summary generated only from the frozen canonical hold-out predictions. It uses
all ten seeds and all four classifiers, reports mean and sample SD, displays
±1 sample SD bands for interpolated TPR, and records the input SHA-256. No
favorable seed or run4 evidence is used.

## Figure 6 publication-freeze output

`figures/figure6/` contains the approved aggregate TreeSHAP summary for the
frozen canonical feature-8 XGBoost model trained with seed 104729. The author
selected 104729 as the first seed in the predefined numerically ordered frozen
seed list, independently of performance. The script verifies the model hash,
metadata, feature order, run5 training metadata, and frozen hold-out split. It
uses 10,000 hold-out observations selected without replacement by deterministic
SHA-256 rank. Native XGBoost 2.1.1 tree-path-dependent TreeSHAP uses no external
background sample. The figure explains the selected classifier's DDoS-class
raw-margin predictions; it is not causation or proof of simulator fidelity.

## Interpretation limitations

The high Normal, UDP-flood, and selected DNS-amplification consistency does not
generalize to every scenario. The principal feature-8 consensus classifiers
missed 8,000 TCP connection-exhaustion DDoS flows. These results diagnose the
behavior of benchmark-trained classifiers under this reconstructed protocol;
they do not establish that simulated and real traffic distributions are
equivalent.
