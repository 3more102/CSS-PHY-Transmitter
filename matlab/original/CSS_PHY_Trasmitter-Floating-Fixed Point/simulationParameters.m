% ----------------------------------------------------------------------- %
% ----------------------------------------------------------------------- %
% Script to set all the Simulation Parameters 
% ----------------------------------------------------------------------- %
% HDL Test Cases ... successe senarios 
% test Case 1 : SNR 12 payloadLength = 20
% test Case 2 : SNR 10 PayloadLength = 55
% test Case 3 : SNR 8  payloadLength = 100  
% test Case 4 : SNR 10 payloadLength = 127  3840*4
% ----------------------------------------------------------------------- %
% Select data rates to simulate
% 0 for 1 Mb/s  , 1  for 250 kb/s
  dataRateArray = [ 0 1 ];  
% ----------------------------------------------------------------------- %
% number of zeros before and after packet to model start time ambiguity
% minimum 3840 Samples
  numZerosBeforePacket = 3840*4;
% number of zeros after packet to leave room for synch error without Matlab
% crash (if synck keeps searching for longer time)
  numZerosAfterPacket = 2000;
% ----------------------------------------------------------------------- %
% number of payload bytes from 1 to 127
  global payloadLength;
    payloadLength  = 25;
% ----------------------------------------------------------------------- %
% selected chirp Sequence Index= 1, 2, 3 or 4
global chirpIndex;
  chirpIndex=1; 
% ----------------------------------------------------------------------- %
% Range of SNR to simulate
  startEbNodB = 8;
  stepEbNodB = 2;
  stopEbNodB = 16;
% ----------------------------------------------------------------------- %
% Detection Threshold
% Ratio of the threshold above the variance of the detector output
  detectionRatio = 4.0;
  doubleDetectionRation = 2 * detectionRatio;
% ----------------------------------------------------------------------- %
% Synchronization Threshold
  syncRatio = 4.0;
% ----------------------------------------------------------------------- %
% Tolerance in verification of timing in synchronization
  syncToleranceSamples = 3;
% ----------------------------------------------------------------------- %
% Fadind model: 0=AWGN, 1=Flat fading, 2= CIR provided by Nanotron
  fadingModel = 0;
% ----------------------------------------------------------------------- %
% If fadingModel =2 select the specific CIR (provided by Nanotron)
%  to simulate selectedCIRindex=1, 2, 3, 4, 5, 6, 7 or 8
% If fadingModel is NOT equal to 2, this parameter has no effect
  selectedCIRindex = 1;
% ----------------------------------------------------------------------- %
% earlylate flag to (1)enable and (0)disable the early late correlation in 
% depreading  Process
%   earlylateflag = 1 ;
% ----------------------------------------------------------------------- %
% Sampling Ratio : sampling Factors used in resampling and downsampling 
  samplingRatio = 1;
% ----------------------------------------------------------------------- %
% phase offset for down sampling must be an integer from 0 to samplingRatio -1.
  RxSamplingPhaseOffset = 0 ;
% ----------------------------------------------------------------------- %
% Frequency offset in PPM
  offsetPPM = 0;  
% ----------------------------------------------------------------------- %
% to Simulae the effect of processing delay added by
% Automatic gain controller 
% This value in microsecond is converted to a number of samples
% (using the sampling frequency) and this number of samples is thrown away
% from the beginning of the preamble
  agcTimeMicroSec =  12 ; 
% ----------------------------------------------------------------------- %
% Number of simulation packets. The higher the better.
% It is recommended not be below 50000 for statistically good results
  numSimulationPackets = 500 ;
% ----------------------------------------------------------------------- %
% Sufficient number of packet erros. For any particular SNR, once this
% number of packet errors is achieved this SNR is stopped. This saves
% considerable simulation time for low SNR values 
  enoughPacketErrors = 200;
% ----------------------------------------------------------------------- %
% Analog to Digital Converter number of bits in the receiver.
global RxADCbitNumber;
RxADCbitNumber = 5;
% ----------------------------------------------------------------------- %
