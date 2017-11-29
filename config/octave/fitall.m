load /home/peter/xpd_data/nov27_2017/test_022.bin_spectra.dat
for pix=1:384
  [y,xmax]=max(spect(pix,3000:3900));
  x=xmax-40+3000:xmax+40+3000;
  y=spect(pix,xmax-40+3000:xmax+40+3000);
  h=0.2;
  [sigmaNew,muNew,Anew]=mygaussfit(x,y,h);
  sigmah(pix)=sigmaNew;
  muh(pix)=muNew;
  Ah(pix)=Anew;
  ycalc=Anew*exp(-(x-muNew).^2/(2*sigmaNew^2));
  plot(x,y);
  hold on;
  plot(x,ycalc);
  pause(0.2);
  hold off
endfor
  save 60kev_fits.dat sigmah muh Ah;
for pix=1:384
  [y,xmax]=max(spect(pix,800:1300));
  x=xmax-40+800:xmax+40+800;
  y=spect(pix,xmax-40+800:xmax+40+800);
  h=0.3;
  [sigmaNew,muNew,Anew]=mygaussfit(x,y,h);
  sigmal(pix)=sigmaNew;
  mul(pix)=muNew;
  Al(pix)=Anew;
  ycalc=Anew*exp(-(x-muNew).^2/(2*sigmaNew^2));
  plot(x,y);
  hold on;                                                                                                        
  plot(x,ycalc);                                                                                                  
  pause(0.2);                                                                                                     
  hold off;
endfor
save 17.5kev_fits.dat sigmal mul Al;

for k=1:384
   f=polyfit([mul(k),muh(k)],[18,60],1);
   g(k,:)=f;
endfor
save ge_fits.dat g;

clf;
for k=1:384
  hold on
   x=[0:4095]*g(k,1)+g(k,2);
   xs(k,1:4096)=x;
   ys(k,1:4096)=k;
   plot(x,(spect(k,:)));
endfor
hold off
save ge_energies.dat xs ys;
figure 2;
mesh(xs,ys,log10(real(spect(1:384,:))));
escale=g(:,1);
figure 3;
plot(sigmah.*escale'.*2.3);
figure 4
plot(sigmal.*escale'.*2.3);
