package ddosvalidation.simulations;

import inet.networklayer.configurator.ipv4.Ipv4NetworkConfigurator;
import inet.node.ethernet.Eth100M;
import inet.node.ethernet.EthernetSwitch;
import inet.node.inet.Router;
import inet.node.inet.StandardHost;

channel ReferenceEth100M extends Eth100M
{
    length = 10m;
}

network DDoSNetwork
{
    parameters:
        int numBenign = default(50);
        int numAttackers = default(20);
        int numReflectors = default(10);
        @display("bgb=1200,760");
    submodules:
        configurator: Ipv4NetworkConfigurator {
            @display("p=70,60");
        }
        accessSwitch: EthernetSwitch {
            parameters:
                numEthInterfaces = parent.numBenign + parent.numAttackers + 1;
                @display("p=360,360");
        }
        edgeRouter: Router {
            parameters:
                numEthInterfaces = 3;
                @display("p=620,360");
        }
        reflectorSwitch: EthernetSwitch {
            parameters:
                numEthInterfaces = parent.numReflectors + 1;
                @display("p=620,620");
        }
        benign[numBenign]: StandardHost {
            parameters:
                numEthInterfaces = 1;
                @display("p=150,150,row,45");
        }
        attacker[numAttackers]: StandardHost {
            parameters:
                numEthInterfaces = 1;
                @display("p=150,520,row,45");
        }
        reflector[numReflectors]: StandardHost {
            parameters:
                numEthInterfaces = 1;
                @display("p=850,650,row,35");
        }
        server: StandardHost {
            parameters:
                numEthInterfaces = 1;
                @display("p=930,360;i=device/server");
        }
    connections:
        for i=0..numBenign-1 {
            benign[i].ethg[0] <--> ReferenceEth100M <--> accessSwitch.ethg[i];
        }
        for i=0..numAttackers-1 {
            attacker[i].ethg[0] <--> ReferenceEth100M <--> accessSwitch.ethg[numBenign + i];
        }
        accessSwitch.ethg[numBenign + numAttackers] <--> ReferenceEth100M <--> edgeRouter.ethg[0];
        edgeRouter.ethg[1] <--> ReferenceEth100M <--> server.ethg[0];
        edgeRouter.ethg[2] <--> ReferenceEth100M <--> reflectorSwitch.ethg[numReflectors];
        for i=0..numReflectors-1 {
            reflector[i].ethg[0] <--> ReferenceEth100M <--> reflectorSwitch.ethg[i];
        }
}
