%-------------------------------------------------------------------------%
%-------------------------------------------------------------------------%
clc
clear all
rand('state',0);
randn('state',0);
%-------------------------------------------------------------------------%
%-------------------------------------------------------------------------%
addpath 'common'
addpath 'transmitter'
%-------------------------------------------------------------------------%
% load cm1_to_8__32MHz.mat 
% figure
% plot(abs(h1))
% title('LOS Residential (CM1)')
%-------------------------------------------------------------------------%
%-*****************  transceiver configurations  ************************-%
%-------------------------------------------------------------------------%
% dataRateArray = [ 0 1 ];  % 0 for  1 Mb/s  , 1  for 250 kb/s
% Set the global Variables for both Transmitter and Receiver 
global chirpIndex ;     % chirp Sequence Index= 1, 2, 3 or 4
global samplingFreqMhz; % Sampling Frequency in MHz
global carrierFreqGHz;  % Carrier frequency in GHz
global codeWordLengthStd;
global preambleLengthStd;
global Tchirp;
global Tsub;

global TxDACbitNumber;
global chirpSequenceNumBit_Rx;
% 
global TxChirpSequencesLength;
%=========================================================================%
%======================== Simulation parameters script ===================%
%=========================================================================%
simulationParameters
%=========================================================================%
EbNodB = [ startEbNodB : stepEbNodB : stopEbNodB ];

%-------------------------------------------------------------------------%
globalSettings();
frequencyOffsetkHz = offsetPPM *carrierFreqGHz;
phaseRotationPerSample = 2*pi*frequencyOffsetkHz/samplingFreqMhz/1000;

%-------------------------------------------------------------------------%
numDataRatesToSimulate = length(dataRateArray);
numSNRlevelsToSimulate = length(EbNodB);

% pre-allocating just for speed simulation
numPacketErrors=zeros(numDataRatesToSimulate,numSNRlevelsToSimulate);
numSimulatedPackets=zeros(numDataRatesToSimulate,numSNRlevelsToSimulate);
numSyncPassedPackets=zeros(numDataRatesToSimulate,numSNRlevelsToSimulate);
sumFreqOffsetHz=zeros(numDataRatesToSimulate,numSNRlevelsToSimulate);
sumSNR_estimationErrordB_Squared = zeros(numDataRatesToSimulate,numSNRlevelsToSimulate);
sumFreqOffsetHzSquared=zeros(numDataRatesToSimulate,numSNRlevelsToSimulate);
[CIRmatrix ] = CIRselection( selectedCIRindex );

%profile on
%-------------------------------------------------------------------------%
for numDataRate = 1 : numDataRatesToSimulate
%-------------------------------------------------------------------------%
dataRate = dataRateArray(numDataRate);
%=========================================================================%
if dataRate == 0 
     rate = '1 Mb/s';
     codingRate = 3/4;  % 1 Mb/s code rate of block coding
     codeWordLength = codeWordLengthStd(1);
else
     rate = '250 kb/s';
     codingRate = 6/32;  % 250 kb/s code rate of block coding
     codeWordLength = codeWordLengthStd(2);
end
% Find the number of samples in preamble
numPreambleSamples=preambleLengthStd(dataRate+1)*Tchirp/4;
%-------------------------------------------------------------------------%
tic
%-------------------------------------------------------------------------%
% This function generates the chirp sequence which consists of 4 chirp
% subsequences, accroding to equation (1a) and figure 20c
chirpSequence = chirpSequenceGenerator(chirpIndex, samplingFreqMhz );
% ####################################################################### %
% ----------------- Fixed Point Representation -------------------------- %
% put chirp sequence samples in (TxDACbitNumber)signed bit integer.
chirpSequence_Tx = floor ( chirpSequence * (2^(TxDACbitNumber -1)-1) ) ;
%-------------------------------------------------------------------------%
% ###################### file Input Output ############################## %
            chirpSequenceReal_tofile = real(chirpSequence_Tx(1:end));
            chirpSequenceImag_tofile = imag(chirpSequence_Tx(1:end));
            re = fi(chirpSequenceReal_tofile,1,6,0);
            im = fi(chirpSequenceImag_tofile,1,6,0);
            
            for n = 1 : length(chirpSequenceReal_tofile)
                bin2comreal(n,:) = bin(re(n));
                bin2comimag(n,:) = bin(im(n));
            end
            fid = fopen('chirpSequenceReal_tofile.txt', 'wt' );
            fprintf(fid, '%c%c%c%c%c%c\n',transpose (bin2comreal));
            fclose (fid);
            
            fid = fopen('chirpSequenceImag_tofile.txt', 'wt' );
            fprintf(fid, '%c%c%c%c%c%c\n',transpose (bin2comimag));
            fclose (fid);
% ###################### file Input Output ############################## %
%-------------------------------------------------------------------------%
% chirpSequence_Tx = chirpSequence_Tx / (2^(TxDACbitNumber -1)-1);
% ####################################################################### %

energyPerSubChirp=sum(sum(abs(chirpSequence_Tx).^2))/4;
%-------------------------------------------------------------------------%
%-------------------------------------------------------------------------%
%-------------------------------------------------------------------------%
end


