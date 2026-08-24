function [ raisedCosine ] =raisedCosineGen(Tsub )
% ----------------------------------------------------------------------- %
% ======================================================================= %
% 6.5a.4.4 Raised cosine window for chirp pulse shaping
% ======================================================================= %
% ----------------------------------------------------------------------- %
% The raised-cosine time-window described by Equation (1c) shall be used 
% to shape the subchirp. The raised cosine window PRC(t) is applied to  
% every subchirp signal in the time domain
% ----------------------------------------------------------------------- %
% The raised cosine pulse shape is sampled at sampling frequnecy every Ts
% first positive sampling time is assumed Ts/2
% ----------------------------------------------------------------------- %
% samples with value 1
% start from time 0 to <= (0.3 Tsub)Ts
% ----------------------------------------------------------------------- %
nunONESsamples=1+floor(0.3*Tsub);
flatPart=ones(1,nunONESsamples);
% ----------------------------------------------------------------------- %
% Number of elements in roll down part
numRollDownSamples= Tsub/2 - nunONESsamples;
% Roll down samples start from time > (0.3 Tsub - 0.5)Ts to >= (0.5 Tsub)Ts
n = [nunONESsamples:nunONESsamples+numRollDownSamples];
rollDown=0.5*( 1 + cos(5*pi/Tsub*(n  - 0.3*Tsub) ) );
% ----------------------------------------------------------------------- %
% concatenate the ones part and the roll down part 
tmp=[flatPart , rollDown];
% The negative index part is the mirror image of the positive index part
raisedCosine=[fliplr(tmp), tmp(2:Tsub/2)];
%-***********************************************************************-%
%-***********************************************************************-%
end




