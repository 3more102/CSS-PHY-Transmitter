
function globalSettings () 
%-------------------------------------------------------------------------%
%=========================================================================%
% globalSettings : Function Summary
%-------------------------------------------------------------------------%
% function used by both transmitter and receiver to set the common
% variables for them depending on Data Rate.
%=========================================================================%
%-------------------------------------------------------------------------%
global preambleLengthStd ;
global SFD_Std ;
global Diff_SFD_Std;
global SFDlength ;
global PHRlength ;

global numBitsPerCodeWordStd ;
global codeWordLengthStd ;
global codeword_1Mbs;
global codeword_250kbs;

global Tchirp;
global Tsub;
global Tgap ;
global chirpIndex;  

global samplingFreqMhz;
global carrierFreqGHz;

global TxDACbitNumber;
global chirpSequenceNumBit_Rx;

global F;
%-------------------------------------------------------------------------%
%=========================================================================%
%  6.5a.3.1 Preamble
%=========================================================================%
%-------------------------------------------------------------------------%
% The preamble sequence from Table 26d should be applied directly to both
% I input and the Q input of QPSK.as specified in Table 26d.
% codeWordLength represent number of chip/symbol 
% The preamble for 1 Mb/s consists of 8 chirp symbols, ones(0:31).
% The preamble for 250 kb/s consists of 20 chirp symbols, ones(0:79).
preambleLengthStd = [ 32 80 ];
%-------------------------------------------------------------------------%
%=========================================================================%
%  6.3.2 SFD field
%=========================================================================%
%-------------------------------------------------------------------------%
SFDlength = 16;
% Start-of-frame delimiter (SFD) bit sequences for the CSS PHY type are 
% defined in Table 20a. Different SFD sequences are defined for the two 
% different data rates.
% A SFD sequence from Table 20a shall be applied directly to both inputs 
% (I and Q) of the QPSK mapper. A SFD sequence starts with bit 0.
    SFD_Std = [  ...
          % The SFD for 1 Mb/s.  
            -1  1  1  1 -1  1 -1 -1  1 -1 -1  1  1  1 -1 -1 ;
          % The SFD for 250 kb/s.
            -1  1  1  1  1 -1  1 -1 -1 -1  1 -1 -1 -1  1  1 ];
        
    Diff_SFD_Std = [  ...
          % The SFD for 1 Mb/s.  
            -1  1  1  1  1  1 -1 -1  1 -1  1 -1  1 -1 -1  1 ;
          % The SFD for 250 kb/s.
            -1  1  1  1 -1 -1  1 -1  1  1  1  1 -1 -1  1  1 ];
        
        
%-------------------------------------------------------------------------%   
%-***********************************************************************-%
%=========================================================================%
% 6.5a.3.3 PHY header (PHR): The format of the PHR is shown in Figure 20b.
%=========================================================================%
%-------------------------------------------------------------------------%
PHRlength = 12;
%=========================================================================%
%  Code Word Length
%=========================================================================%
%-------------------------------------------------------------------------%
% Each 3-bit data symbol shall be mapped onto a 4-chip
% Each 6-bit data symbol shall be mapped onto a 32-chip 
codeWordLengthStd = [ 4 32 ] ;
%-------------------------------------------------------------------------%
%=========================================================================%
% Standrad Code word table generation 
%=========================================================================%
%-------------------------------------------------------------------------%
% generate the Bi-Orthogonal sequences in tables 26a and 26b
% codeword(c0, c1, c2, c3) for the 1 Mb/s data rate as in Table26a. 
StandCodeWord_1Mbs = hadamard ( codeWordLengthStd(1) ) ;
codeword_1Mbs = [StandCodeWord_1Mbs;-StandCodeWord_1Mbs];
%-------------------------------------------------------------------------%
% ###################### file Input Output ############################## %
fid = fopen('codeword_1Mbs.txt', 'wt' );
fprintf(fid, '%d%d%d%d\n', transpose((codeword_1Mbs+1)/2));
fclose (fid);
% ###################### file Input Output ############################## %
%-------------------------------------------------------------------------%

% codeword (c0, c1, c2, ... , c31) for the optional 250 kb/s data rate 
% as specified in Table 26b.
StandCodeWord_250kbs = hadamard ( codeWordLengthStd(2) ) ;
codeword_250kbs = [StandCodeWord_250kbs;-StandCodeWord_250kbs];
%-------------------------------------------------------------------------%
% ###################### file Input Output ############################## %
fid = fopen('codeword_250kbs.txt', 'wt' );
fprintf(fid, '%d%d%d%d\n', transpose((codeword_250kbs+1)/2));
fclose (fid);
% ###################### file Input Output ############################## %
%-------------------------------------------------------------------------%

%-------------------------------------------------------------------------%

%=========================================================================%
%  Number of bits per Code Word
%=========================================================================%
% ----------------------------------------------------------------------- %
%  a data symbol shall consist of 3 bits. i.e.,numBitsPerCodeWord=3.
%  a data symbol shall consist of 6 bits. i.e.,numBitsPerCodeWord=6.
 numBitsPerCodeWordStd = [ 3 6 ];
% ----------------------------------------------------------------------- %
% ----------------------------------------------------------------------- %
samplingFreqMhz=32;  % Sampling Frequency in MHz
carrierFreqGHz=2.45; % Carrier frequency in GHz
% ----------------------------------------------------------------------- %
% ----------------------------------------------------------------------- %
% Table 26g�Equation (1a) numerical parameters�timing parameters
% timing parameters values Multiple of 1/32MHz
% Tchirp 6 us 
% Tsub 1.1875 us 
% T1 = 1468.75 us 
% T2 = 2312.5 ns 
% T3 = 4156.25 ns 
% T4 = 0 ns 
% ----------------------------------------------------------------------- %
Tchirp= 6 * samplingFreqMhz;
Tsub = 1.1875 * samplingFreqMhz;
Tau_m = [0.46875, 0.3125, 0.15625, 0]* samplingFreqMhz;
% ----------------------------------------------------------------------- %
% ----------------------------------------------------------------------- %
% 6.5a.4.2 Active usage of time gaps
% ----------------------------------------------------------------------- %
% ----------------------------------------------------------------------- %
% In conjunction with the subchirp sequence , Different pairs of time gaps 
% are defined. The time gaps are chosen to make the four sequences even 
% closer to being orthogonal. The time gaps shall be applied alternatively 
% between subsequent chirp symbols as shown  in Figure 20d. 
% The values of the time gaps are calculated from the timing parameters 
% specified in Table 26g (in 6.5a.4.3). 
Tgap(1) = Tchirp - 4*Tsub - 2*Tau_m(chirpIndex);
Tgap(2) = Tchirp - 4*Tsub + 2*Tau_m(chirpIndex);
% ----------------------------------------------------------------------- %
% Analog to Digital Converter Resolution.
% digital to analogue converter number of bits in Transmitter 
% ----------------------------------------------------------------------- %
TxDACbitNumber = 6 ;
chirpSequenceNumBit_Rx = 6 ;
% ----------------------------------------------------------------------- %
% ----------------------------------------------------------------------- %
% % ======================================================================= %
% % function to set the different parameters of the Fi Matlab Toolbox
% % ======================================================================= %
% % issues warning when overflow occurs
% warning on  fi:overflow 
% % issues warning when underflow occurs
% warning off fi:underflow 
% % Turn this on to see the line number in the code where the 
% % overflow occurred 
% warning on backtrace
% reset(fipref);
% fipref('LoggingMode','on');
% % ======================================================================= %
% % ----------------------------------------------------------------------- %
% % fimath Properties
% % ----------------------------------------------------------------------- %
% % OverflowMode : Overflow-handling mode
% % saturate : Saturate to maximum or minimum value of the 
% % fixed-point range on overflow.
% % wrap : Wrap on overflow. This mode is also known as two's 
% % complement overflow.
% % select warp easiest to Hardware Implementation
% % RoundMode : The rounding mode 
% % ( ceil , convergent , fix , floor , nearest , round )
% % select floor easiest to Hardware Implementation.
% F = fimath('OverflowMode','wrap','RoundMode','floor');
% % ----------------------------------------------------------------------- %
% ----------------------------------------------------------------------- %
end
