import os
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import User, Teacher, Base, DATABASE_URL

# Connect to database
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

# Department to Branch Mapping
DEPT_MAP = {
    "Production Engineering": "Production Engineering",
    "Mechanical Engineering": "Mechanical Engineering",
    "Civil & Environmental Engg": "Civil Engineering",
    "Computer Engineering & IT": "Computer Science",
    "Electrical / Electronics Engg": "Electronics Engineering",
    "Textile Engineering": "Textile Engineering"
}

csv_data = """Department,Faculty Name,Designation,Qualification,Specialization,Email,Phone,Role
Production Engineering,Dr. Dadarao N. Raut,Professor,"M.Tech, Ph.D. (Mechanical-CAD-CAM), MBA (Operations/HR), LLB",Manufacturing / Industrial Engineering,dnraut@pe.vjti.ac.in,24198239,Professor & HOD
Production Engineering,Dr. Madhukar R. Nagare,Associate Professor,"M.Tech, Ph.D. (Machine Tools)","Metal Forming Technology, Supply Chain Management",mrnagare@pe.vjti.ac.in,24198237,Permanent
Production Engineering,Dr. Dattaji K. Shinde,Associate Professor,"M.Tech (IIT Delhi), Ph.D. (Nano Engg., NCAT USA)","Composite Materials, Nanoengineering",dkshinde@pe.vjti.ac.in,24198235,Permanent
Production Engineering,Dr. Pirsab R. Attar,Assistant Professor,"M.Tech, Ph.D. (Mechanical, IIT Delhi)",Manufacturing Processes,prattar@pe.vjti.ac.in,24198240,Permanent
Production Engineering,Mr. Duryodhan V. Pendam,Assistant Professor,"M.Tech, Pursuing Ph.D. (NITIE Mumbai)",Industrial Engineering,dvpendam@pe.vjti.ac.in,24198240,Permanent
Production Engineering,Dr. Vishwadeep C. Handikherkar,Assistant Professor,"M.Tech, Ph.D.",,vishwadeepch@pe.vjti.ac.in,,Permanent
Production Engineering,Dr. Srinath E. Gudur,Assistant Professor,"M.Tech, Ph.D.","Metal Additive Manufacturing, Laser Forming, Hybrid Manufacturing",segudur@pe.vjti.ac.in,,Permanent
Production Engineering,Dr. Ramchandra P. Une,Professor of Practice,Ph.D.,,,,Professor of Practice
Production Engineering,Dr. Mugdha D. Dongre,Assistant Professor (Tenure),"M.E., Ph.D.",Additive Manufacturing,mddongre@pe.vjti.ac.in,,Tenure
Production Engineering,Dr. N. Thirupathi,Assistant Professor (Tenure),"M.E., Ph.D.",Advanced Manufacturing Processes,nthirupathi@pe.vjti.ac.in,,Tenure
Production Engineering,Dr. Arijit Sinhababu,Assistant Professor (Tenure),"M.Tech, Ph.D.",Computational Materials Science,asinhababu@pe.vjti.ac.in,,Tenure
Production Engineering,Dr. Arindam Ghosal,Assistant Professor (Tenure),"M.E., Ph.D.","Micro Machining, Industrial Materials & Metallurgy",aghosal@pe.vjti.ac.in,,Tenure
Production Engineering,Mr. Vishal W. Bhagat,Assistant Professor (Adhoc),M.Tech,Manufacturing Engineering,vwbhagat@pe.vjti.ac.in,,Adhoc
Production Engineering,Mr. Nilesh Y. Chanewar,Assistant Professor (Adhoc),M.E.,Manufacturing Systems & Engineering,nychanewar@pe.vjti.ac.in,,Adhoc
Production Engineering,Mr. Netaji R. Kadam,Assistant Professor (Adhoc),M.Tech,Production Engineering,nrkadam@pe.vjti.ac.in,,Adhoc
Production Engineering,Dr. Mahendra U. Gaikwad,Assistant Professor (Adhoc),"M.E., Ph.D.",Advanced Manufacturing Processes,mugaikwad@pe.vjti.ac.in,,Adhoc
Production Engineering,Mrs. Akshata J. Jadhav,Assistant Professor (Adhoc),M.Tech,CAD/CAM & Robotics,ajjadhav@pe.vjti.ac.in,,Adhoc
Production Engineering,Dr. B.N. Sontakke,Assistant Professor (Tenure),"Ph.D. (Mechanical, COEP Pune)",,bnsontakke@pe.vjti.ac.in,,Tenure
Production Engineering,Dr. P.A. Rajwade,Assistant Professor (Tenure),"M.Tech (SVNIT Surat), Ph.D. (Mechanical Engg, IIT Mumbai)",,parajiwade@pe.vjti.ac.in,,Tenure
Production Engineering,Dr. Dipak G. Wagre,Assistant Professor (Tenure),"M.Tech (IIT Delhi), Ph.D. (Univ. of Porto, Portugal)",,dgwagre@pe.vjti.ac.in,,Tenure
Mechanical Engineering,Dr. Sachin S. Naik,Associate Professor & HOD,"B.E. (Mechanical), M.Tech (Design Engg), Ph.D. (Mechanical)","Vibration & Dynamics, Fracture Mechanics, Mechanical Design",ssnaik@me.vjti.ac.in,24198221,HOD (Associate Professor)
Mechanical Engineering,Dr. W.S. Rathod,Associate Professor,"B.E. (Metallurgy), M.E. (Production Engg), Ph.D. (Metallurgy)","Physical Metallurgy, Surface Engineering, High Temp. Coating",wsrathod@me.vjti.ac.in,24198229,Permanent
Mechanical Engineering,Dr. R.M. Tayade,Associate Professor,"D.M.E., B.E. Mech, M.E. Mech (Machine Design), Ph.D.","Non-traditional Micro-machining, Manufacturing, IC Engines",rmtayade@me.vjti.ac.in,24198430,Permanent
Mechanical Engineering,Dr. V.M. Phalle,Associate Professor,"B.E. Mech, M.E. Mech (Machine Design), Ph.D. (Mechanical)","Machine Design, Tribology, Vibration, Kinematics",vmphalle@me.vjti.ac.in,24198122,Permanent
Mechanical Engineering,Dr. N.P. Gulhane,Associate Professor,"M.E. (Mechanical), Ph.D. (Thermal Engg)","Microfluidics, Heat Transfer, Solar Engg., CFD, MEMS",npgulhane@me.vjti.ac.in,24198200,Associate Professor & TPO
Mechanical Engineering,Dr. A.V. Deshpande,Associate Professor,"B.E. (Mechanical), M.E. (Mechanical), Ph.D. (Mechanical)","Fluid Mechanics, CFD, Gas Dynamics, Fluid Machinery",avdeshpande@me.vjti.ac.in,24198217,Permanent
Mechanical Engineering,Dr. S.A. Mastud,Associate Professor,"M.Tech (Production Engg), Ph.D. (Manufacturing)","Manufacturing Processes, 3D Printing, AI-ML for Manufacturing, Micro-Manufacturing",samastud@me.vjti.ac.in,24198205,Permanent
Mechanical Engineering,Dr. P.M. Karande,Associate Professor,"M.E. (Production), Ph.D.","Decision Sciences, MCDM Supplier Selection",pmkarande@me.vjti.ac.in,24198109,Associate Professor & Controller of Exam (Degree)
Mechanical Engineering,Dr. V.B. Suryawanshi,Assistant Professor,"M.E. (Mechanical), Ph.D.","Advanced Composite Materials, Additive Manufacturing, Nanomaterials, FEA",vbsuryawanshi@me.vjti.ac.in,,Permanent
Mechanical Engineering,Dr. H.P. Khairnar,Assistant Professor,"M.E. (Mechanical), Ph.D. (Mechanical)","Tribology, Automobile Engineering",hpkhairnar@me.vjti.ac.in,24198204,Permanent
Mechanical Engineering,Dr. A.S. Rao,Assistant Professor,"M.E. (Mechanical), Ph.D.","CAD/CAM, Robotics, Automation, Rapid Product Development",asrao@me.vjti.ac.in,24198410,Permanent
Mechanical Engineering,Dr. M.V. Tendolakar,Assistant Professor,"M.E. (Mechanical), Ph.D.","Thermal Engineering, Refrigeration & AC, Cryogenics",mvtendolkar@me.vjti.ac.in,24198209,Permanent
Mechanical Engineering,Dr. P.A. Wankhade,Assistant Professor,"M.E. (Mechanical), Ph.D. (Advanced Heat Transfer)","Automobile Engg., Hybrid Electric Vehicles, Non-Fourier Heat Transfer",pawankhade@me.vjti.ac.in,24198227,Permanent
Mechanical Engineering,Prof. S.S. Barve,Assistant Professor,"M.E. (Mechanical), Pursuing Ph.D.","Machine Design, Vibration, Tribology, Material Engineering",ssbarve@me.vjti.ac.in,24198208,Permanent
Mechanical Engineering,Dr. S.G. Jadhav,Assistant Professor,Ph.D.,Machine Design,sgjadhav@me.vjti.ac.in,24198211,Permanent
Mechanical Engineering,Dr. G.U. Tembhare,Assistant Professor,"M.E. (Mechanical), Ph.D. (Design Engineering)","Machine Design, FEM, Mechanical Vibration, Solid Mechanics",gutembhare@me.vjti.ac.in,24198209,Permanent
Mechanical Engineering,Prof. S.P. Gajre,Assistant Professor,M.Tech,"Additive Manufacturing, Robotics & Automation, Manufacturing Engg.",spgajre@me.vjti.ac.in,24198205,Permanent
Mechanical Engineering,Dr. Suresh Jadhav,Assistant Professor,"Ph.D. (Mechanical Machine Design, IITR)","Tribology, Bio-tribology, Surface Engineering, Nano-tribology",sgjadhav@me.vjti.ac.in,,Permanent
Mechanical Engineering,Dr. Ram Rao,Professor of Practice,Ph.D.,,,,Professor of Practice
Mechanical Engineering,Mr. Shreyas Bakshi,Professor of Practice,,,,,Professor of Practice
Mechanical Engineering,Abhijit Mitra,Assistant Professor (Tenure),Ph.D.,"Fluid Dynamics, Aerodynamics, Flow Transition, Turbomachinery",amitra@me.vjti.ac.in,,Tenure
Mechanical Engineering,Arif Varsi,Assistant Professor (Tenure),Ph.D.,"CAD/CAM, Unconventional Machining Processes",amvarsi@me.vjti.ac.in,,Tenure
Mechanical Engineering,Dr. Nishit Bedi,Assistant Professor (Tenure),Ph.D.,"Microflows, Heat Transfer and Fluid Flow, CFD",nbedi@me.vjti.ac.in,,Tenure
Mechanical Engineering,Vaibhav Shinde,Assistant Professor (Tenure),"B.E. (Mech), M.E. (Mech-Design), Ph.D. (Mech)","Machine Design, FEA, Optimisation",vshinde@me.vjti.ac.in,,Tenure
Mechanical Engineering,Dr. P.A. Rajiwade,Assistant Professor (Tenure),Ph.D.,"Thermal & Fluid Flow, Computational Aerodynamics, Supersonic Jet Impingement",parajiwade@me.vjti.ac.in,,Tenure
Mechanical Engineering (Diploma),Dr. R.S. Kadge,Lecturer / Dean Diploma,"M.Tech (Mechanical), Ph.D.",Machine Design,rskadge@me.vjti.ac.in,24198211,Dean Diploma
Mechanical Engineering (Diploma),Dr. V.N. Palaskar,Lecturer (Diploma HOD),"M.E. (Mech), Ph.D. (Mech)","Machine Design, Hybrid Solar Thermal & PV System",vnpalskar@me.vjti.ac.in,24198228,Diploma HOD
Mechanical Engineering (Diploma),Dr. R.O. Bhagwat,Lecturer,"M.E. (Mechanical), Ph.D. (Production Engg)","Industrial Management, Manufacturing Technology",robhagwat@me.vjti.ac.in,24198213,Permanent Lecturer
Mechanical Engineering (Diploma),Prof. S.D. Rote,Lecturer,M.E. (Production),Industrial Engg. & Management,sdrote@me.vjti.ac.in,24198215,Permanent Lecturer
Mechanical Engineering (Diploma),Prof. A.R. Dhiware,Lecturer,M.Tech (IIT Goa),Mechanical Science,ardhiware@me.vjti.ac.in,24198226,Permanent Lecturer
Mechanical Engineering (Diploma),Dr. V.M. Barethiye,Lecturer,"M.E. (Mechanical), Ph.D. (JU Kolkata)",Automotive Suspension System,vmbarethiye@me.vjti.ac.in,24198216,Permanent Lecturer
Mechanical Engineering (Diploma),Prof. Y.A. Ingale,Adhoc Faculty,M.Tech (Mechanical Engg.),"Design Engg, Manufacturing Processes, Engine Testing, Mechatronics",yingale@me.vjti.ac.in,8055752331,Adhoc
Mechanical Engineering (Diploma),Prof. N.E. Chaudhari,Adhoc Faculty,M.Tech,"Manufacturing Processes, Engineering Graphics, Materials Science",nechaudhari@me.vjti.ac.in,,Adhoc
Mechanical Engineering (Diploma),Prof. D.S. Pol,Adhoc Faculty,M.Tech,Automobile Engineering,dpol@me.vjti.ac.in,,Adhoc
Mechanical Engineering (Diploma),Prof. V.B. Wagh,Adhoc Faculty,M.E. (Mechanical),Design Engineering,vbwagh@me.vjti.ac.in,,Adhoc
Civil & Environmental Engg,Dr. Mhaske S.Y.,Associate Professor & HOD,Ph.D.,Geospatial Technology,symhaske@ci.vjti.ac.in,,HOD (Associate Professor)
Civil & Environmental Engg,Dr. Wayal A.S.,Associate Professor,Ph.D.,Water Resource Engineering,aswayal@ci.vjti.ac.in,24198135/24198140,Permanent
Civil & Environmental Engg,Prof. Chaudhari P.S.,Assistant Professor,M.Tech,Water Resource Engineering,pschaudhari@ci.vjti.ac.in,24198146,Permanent
Civil & Environmental Engg,Dr. Sayyad Sameer U.,Assistant Professor,"M.E., Ph.D.",Environmental Engineering,susayyad@ci.vjti.ac.in,24198336,Permanent
Civil & Environmental Engg,Dr. Varekar Vikas B.,Assistant Professor,Ph.D.,Environmental Engineering,vbvarekar@ci.vjti.ac.in,24198148,Permanent
Civil & Environmental Engg,Dr. Chandrashekhar D. Wagh,Assistant Professor,Ph.D.,Infrastructure Engineering Management,cdwagh@ci.vjti.ac.in,,Permanent
Civil & Environmental Engg,Dr. Sreyashrao S. Surapreddi,Assistant Professor,Ph.D.,Transportation Geotechnology,sssurapreddi@ci.vjti.ac.in,,Permanent
Civil & Environmental Engg,Dr. Ninad N. Oke,Assistant Professor,Ph.D.,Environmental Engineering,nnoke@ci.vjti.ac.in,,Permanent
Civil & Environmental Engg,Dr. P.P. Bhave,Adjunct Professor,Ph.D.,,ppbhave@ci.vjti.ac.in,,Adjunct
Civil & Environmental Engg,Dr. Vijay Joshi,Professor of Practice,Ph.D.,,,,Professor of Practice
Civil & Environmental Engg,Mr. Yogendra Naik,Professor of Practice,,,,,Professor of Practice
Civil & Environmental Engg,Dr. Sheelu Verghese,Assistant Professor (Tenure),Ph.D.,Environmental Engineering,sverghese@ci.vjti.ac.in,,Tenure
Civil & Environmental Engg,Dr. Annie Joy,Assistant Professor (Tenure),Ph.D.,Geotechnical Engineering,ajoy@ci.vjti.ac.in,,Tenure
Civil & Environmental Engg,Dr. Megha Sharma,Assistant Professor (Tenure),Ph.D.,,mmsharma@ci.vjti.ac.in,,Tenure
Civil & Environmental Engg,Nandini S. Shirbhate,Assistant Professor (Adhoc),M.Tech,Environmental Engineering,nssshirbhate@ci.vjti.ac.in,,Adhoc
Civil & Environmental Engg,Vandanaben V. Kotak,Assistant Professor (Adhoc),M.Tech,Infrastructure Engineering and Technology,vvkotak@ci.vjti.ac.in,,Adhoc
Civil & Environmental Engg,Anjum Attar,Assistant Professor (Adhoc),M.Tech,,adattar@ci.vjti.ac.in,,Adhoc
Civil & Environmental Engg (Diploma),Prof. C.R. Bhole,Lecturer & Incharge Head,"M.E., Pursuing Ph.D.",Pavement Engineering,crbhole@ci.vjti.ac.in,24198144,Diploma Incharge HOD
Civil & Environmental Engg (Diploma),Mrs. Mangrulkar Amruta M.,Lecturer,M.E.,Water Resources Engineering,apgorkar@ci.vjti.ac.in,24198149,Permanent Lecturer
Civil & Environmental Engg (Diploma),Mrs. Bhangale V.S.,Lecturer,M.E.,Environmental Engineering,vsbhangale@ci.vjti.ac.in,24198145,Permanent Lecturer
Civil & Environmental Engg (Diploma),Mrs. Sagole Shweta A.,Lecturer,M.Tech,Geotechnical Engineering,sasagole@ci.vjti.ac.in,24198148,Permanent Lecturer
Civil & Environmental Engg (Diploma),Abhinav Pankaj,Lecturer (Adhoc),M.Tech,Water Resources Engineering,apankaj@ci.vjti.ac.in,,Adhoc
Civil & Environmental Engg (Diploma),Bhagyashri Patil,Lecturer (Adhoc),M.Tech,Environmental Engineering,bapatil@ci.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Dr. R.A. Patil,Associate Professor & HOD (Electronics),Ph.D.,"Signal & Image Processing, AI-ML Applications, IoT, Biomedical",rapatil@el.vjti.ac.in,24198364,HOD (Electronics Degree)
Electrical / Electronics Engg,Dr. R.N. Awale,Professor (Deputy Director),Ph.D.,"Image Processing, Computer Networks, Error Correcting Codes",rnawale@el.vjti.ac.in,24198153,"Professor, Deputy Director, TEQIP-II Coordinator"
Electrical / Electronics Engg,Dr. Faruk A.S. Kazi,Professor,Ph.D.,"Dynamics & Control, Robotics, Cyber Physical Systems",fskazi@el.vjti.ac.in,24198180,Professor & Dean R&D
Electrical / Electronics Engg,Dr. Rahul Ingle,Assistant Professor,Ph.D. (Electronics),"Signal Processing, Biomedical Signal & Image Processing, Data Science",rringle@el.vjti.ac.in,24198174,Assistant Professor & Rector
Electrical / Electronics Engg,Dr. Gajanan Galshetwar,Assistant Professor,Ph.D.,"Computer Vision, IoT, AI/ML, Image & Video Processing",gmgalshetwar@el.vjti.ac.in,,Permanent
Electrical / Electronics Engg,Dr. Neha Mishra,Assistant Professor,"Ph.D., Post Doc.","Bio-MEMS, Bio-Sensors, Microfluidics, VLSI Fabrication, Optical Spectroscopy",nmishra@el.vjti.ac.in,,Permanent
Electrical / Electronics Engg,Dr. Niteshkumar S. Agrawal,Assistant Professor,Ph.D.,"Device Modelling, Sensor Technology, Nanotechnology, Micro/Nano-Fabrication, Optics",nsagrawal@el.vjti.ac.in,,Permanent
Electrical / Electronics Engg,Dr. Mitali V. Shewale,Assistant Professor,Ph.D.,Artificial Intelligence,mvshewale@ee.vjti.ac.in,8446440464,Permanent
Electrical / Electronics Engg,Dr. S.R. Wagh,Assistant Professor & HOD (Electrical),Ph.D.,"Power System Dynamics, Stability and Control",srwagh@ee.vjti.ac.in,24198182/24198186,HOD (Electrical Degree)
Electrical / Electronics Engg,Dr. S.J. Bhosale,Associate Professor,"M.E. (Electrical), Ph.D.","Nano-Optics, Communication",sjbhosale@ee.vjti.ac.in,24198193,Permanent
Electrical / Electronics Engg,Prof. H.B. Chaudhari,Associate Professor,"M.E. (Electrical), Pursuing Ph.D.","High Voltage, Networks, Microprocessor, Control Systems",hbchoudhari@ee.vjti.ac.in,24198180,Permanent
Electrical / Electronics Engg,Prof. Krishna Kanakgiri,Assistant Professor,"M.Tech (Electrical), Pursuing Ph.D.","High Voltage, EMF, Power Systems",kvkanakgiri@ee.vjti.ac.in,24198560,Permanent
Electrical / Electronics Engg,Dr. Pragati Gupta,Assistant Professor,"M.Tech (Electrical), Ph.D.","Power Systems (Deregulation & Market Economy, Stability)",ppgupta@ee.vjti.ac.in,24198172,Permanent
Electrical / Electronics Engg,Dr. Deepak D. Gawali,Assistant Professor,Ph.D.,"Optimization, Control System",ddgawali@ee.vjti.ac.in,9869304153,Tenure
Electrical / Electronics Engg,Dr. Ayush Saxena,Assistant Professor,Ph.D.,"EMF, Control Systems, RF and Microwaves",asaxena@ee.vjti.ac.in,9773728838,Permanent
Electrical / Electronics Engg,Dr. Neha Septa,Assistant Professor (Tenure),Ph.D.,"Wireless Communication, Vehicular Ad-Hoc Network",nsepta@el.vjti.ac.in,8962402512,Tenure
Electrical / Electronics Engg,Dr. Navdeep M. Singh,Adjunct Professor,"M.Tech, Ph.D.","Control Systems, Machine Learning",nmsingh@ee.vjti.ac.in,,Adjunct
Electrical / Electronics Engg,Dr. Rohin Daruwala,Adjunct Professor,"M.E., Ph.D.","Microprocessor Systems, Computer Architecture, IoT",rddaruwala@el.vjti.ac.in,,Adjunct
Electrical / Electronics Engg,Mr. Deepak Ochani,Professor of Practice,,,,,Professor of Practice
Electrical / Electronics Engg,Mr. Girish Jawale,Professor of Practice,,,,,Professor of Practice
Electrical / Electronics Engg,Dr. Sunny Kumar,Assistant Professor (Tenure),Ph.D.,Power System,sskumar@ee.vjti.ac.in,,Tenure
Electrical / Electronics Engg,Dr. Gyanesh Singh,Assistant Professor (Tenure),Ph.D.,Power System,gsingh@ee.vjti.ac.in,,Tenure
Electrical / Electronics Engg,Dr. Hithu Anand,Assistant Professor (Tenure),Ph.D.,Power Electronics and Power System,hanand@ee.vjti.ac.in,,Tenure
Electrical / Electronics Engg,Dr. Sukalyan Maji,Assistant Professor (Tenure),Ph.D.,"Smart Grid, Power System",smaji@ee.vjti.ac.in,,Tenure
Electrical / Electronics Engg,Dr. Dheeraj Kumar Dhaked,Assistant Professor (Tenure),Ph.D.,"Power Systems, AI/ML Applications",dkdhaked@ee.vjti.ac.in,,Tenure
Electrical / Electronics Engg,Dr. Anand Kumar,Assistant Professor (Tenure),Ph.D.,"Control System, Fractional-Order Controller",akumar@ee.vjti.ac.in,,Tenure
Electrical / Electronics Engg,Dr. Mohammad Sartaj,Assistant Professor (Tenure),Ph.D.,Power Electronics and Electric Drives,mdsartaj@ee.vjti.ac.in,,Tenure
Electrical / Electronics Engg,Dr. Haroon Rehman,Assistant Professor (Tenure),Ph.D.,Power Electronics and Electric Drives,hrehman@ee.vjti.ac.in,,Tenure
Electrical / Electronics Engg,Prof. Sunitha Premakumar,Assistant Professor (Adhoc),M.Tech,Power Systems,spremakumar@ee.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Prof. Deepanshu Gupta,Assistant Professor (Adhoc),M.Tech,Power Systems,dgupta@ee.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Prof. Shubham Bhadre,Assistant Professor (Adhoc),M.Tech,Power Electronics and Power Systems,spbhadre@ee.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Prof. Sneha Chautmol,Assistant Professor (Adhoc),M.E.,Electrical Power System,sachautmol@ee.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Prof. Aishwarya Rajendra Awhad,Assistant Professor (Adhoc),M.Tech,Integrated Power System,arawhad@ee.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Prof. Shashank Verma,Assistant Professor (Adhoc),M.Tech,"Control System, Computer Vision, AI/ML",ssverma@ee.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Dr. Snehlata Yadav,Assistant Professor (Tenure),Ph.D.,Semiconductor Device Modeling and Simulation,syadav@et.vjti.ac.in,,Tenure
Electrical / Electronics Engg,Dr. Ravindrakumar Maurya,Assistant Professor (Tenure),Ph.D.,"Semiconductor Device Modeling, Analog Circuit Design, NC-FinFET",rkmaurya@el.vjti.ac.in,,Tenure
Electrical / Electronics Engg,Dr. Anusaka Gon,Assistant Professor (Tenure),Ph.D.,Digital VLSI Design,angon@el.vjti.ac.in,,Tenure
Electrical / Electronics Engg,Dr. Vivek Ramakrishnan,Assistant Professor (Adhoc),Ph.D.,"DSP, Image Processing",vramakrishnan@el.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Prof. Bharati Bhirud,Assistant Professor (Adhoc),M.E.,"Communication, Computer Communication Network, Cybersecurity",bnbhirud@el.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Prof. Mithileshkumar R. Yadav,Assistant Professor (Adhoc),M.Tech,"Cyber Security, AI/ML, Communication",mryadav@ee.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Prof. Zohra Bano Khan,Assistant Professor (Adhoc),M.Tech,Radar Signal Processing and Imaging,zkhan@ee.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Prof. Sonal Gedam,Assistant Professor (Adhoc),M.Tech,"Control System, Data Science, AI/ML, Communication",smgedam@ee.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Prof. Parvathy Lakshmy,Assistant Professor (Adhoc),M.Tech,Signal Processing,plakshmy@el.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Prof. Mayuri Mathpati,Assistant Professor (Adhoc),M.S. (Embedded System Engg.),Assembly and Packaging (Material Science),mrmathpati@el.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Prof. Shweta Kondvilkar,Assistant Professor (Adhoc),M.Tech,Wireless Communication,slkondvilkar@et.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Prof. Amey Nandgaonkar,Assistant Professor (Adhoc),M.Tech (Data Science & Engg),"Data Science, AI/ML",aanandgaonkar@et.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Prof. Bhimrao Jadhao,Assistant Professor (Adhoc),"M.Tech, Ph.D. Pursuing","Antennas, RF/Microwave and Radar",bsjadhao@el.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Prof. Sneha Addanki,Assistant Professor (Adhoc),M.Tech,Electronics,,,Adhoc
Electrical / Electronics Engg,Prof. Dimple Chaudhari,Assistant Professor (Adhoc),M.E.,"Digital Electronics, Signal Processing, Embedded Systems",djchaudhari@el.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Prof. Sapna Gahlot,Assistant Professor (Adhoc),M.Tech,Power Electronics & Drives,sgahlot@el.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Prof. Suyog R. Hawal,Assistant Professor (Adhoc),M.Tech,"Nano Photonics, Semiconductor Devices, Climate Change",srhawal@ee.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Prof. Rohit Khadkikar,Assistant Professor (Adhoc),M.Tech,"Basic Electronics, Industrial Measurement System",rmkhadkikar@el.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Prof. Niranjan Joshi,Assistant Professor (Adhoc),M.Tech (EXTC),RF and Antenna,nmjoshi@ee.vjti.ac.in,,Adhoc
Electrical / Electronics Engg,Prof. Sarang Oak,Assistant Professor (Adhoc),M.Tech (Electronics Engg.),"Power Electronics, Digital Electronics, Instrumentation",ssoak@ee.vjti.ac.in,9869351224,Adhoc
Electrical / Electronics Engg (Diploma),Dr. Yogesh Wankhede,Diploma Electronics HOD (Lecturer),Ph.D.,"Computer Architecture, Embedded System",yewankhede@el.vjti.ac.in,24198509,Diploma Electronics HOD
Electrical / Electronics Engg (Diploma),Dr. Jyoti Gondane,Lecturer,Ph.D.,"Instrumentation, Automation, Optical Sensing/Detection System",jagondane@el.vjti.ac.in,,Permanent Lecturer
Electrical / Electronics Engg (Diploma),Prof. Ami Brahmbhatt,Lecturer,M.Tech,"Data Networking, Electronic Communication",apbrahmbhatt@el.vjti.ac.in,24198177,Permanent Lecturer
Electrical / Electronics Engg (Diploma),Dr. Vikram Kehri,Lecturer,Ph.D. (Electronics),"Network Analysis, IoT, Biomedical Signal Processing",vakehri@el.vjti.ac.in,24198174,Permanent Lecturer
Electrical / Electronics Engg (Diploma),Dr. S.K. Bhil,Diploma Electrical HOD (Lecturer),Ph.D. (Electrical Engg),"Power System, Switchgear and Protection",skbhil@ee.vjti.ac.in,24198188,Diploma Electrical HOD
Electrical / Electronics Engg (Diploma),Mrs. S.R. Yadwad,Lecturer & Dean Diploma,B.E. (Electrical),Electrical Measurement,sryadwad@ee.vjti.ac.in,24198187,Dean Diploma (Electrical)
Electrical / Electronics Engg (Diploma),Prajkta Y. Deshbhratar,Lecturer,"B.E. (Electronics), M.Tech (Power Systems)",Power Systems,pydeshbhratar@ee.vjti.ac.in,,Permanent Lecturer
Electrical / Electronics Engg (Diploma),Prof. Navneet Nikalje,Assistant Professor,M.E.,Communication,navneet@el.vjti.ac.in,7208771219,Adhoc
Electrical / Electronics Engg (Diploma),Prof. Pooja Baikar,Assistant Professor,M.E.,Electronics and Telecommunication,prbaikar@el.vjti.ac.in,9769899170,Adhoc
Electrical / Electronics Engg (Diploma),Prof. Kalyani Ketkar,Assistant Professor,M.Tech,Electronics,krketkar@el.vjti.ac.in,9619831991,Adhoc
Electrical / Electronics Engg (Diploma),Prof. Snehal Kamble,Assistant Professor,M.Tech,Electronic Design and Technology,sbkamble@el.vjti.ac.in,7796899724,Adhoc
Electrical / Electronics Engg (Diploma),Prof. Shanmugasundaram Konar,Assistant Professor,M.E.,Electronics,skonar@el.vjti.ac.in,,Adhoc
Electrical / Electronics Engg (Diploma),Prof. Kaushal Sontakke,Assistant Professor,M.Tech,Electrical Power System Engineering,kbsontakke@ee.vjti.ac.in,8275225413,Adhoc
Electrical / Electronics Engg (Diploma),Prof. Prajakta Gondane,Assistant Professor,M.Tech,Integrated Power System,pydeshbhratar@ee.vjti.ac.in,,Adhoc
Electrical / Electronics Engg (Diploma),Prof. Shubham Kamble,Assistant Professor,M.Tech,Power Electronics and Power System,sdkamble@ee.vjti.ac.in,,Adhoc
Electrical / Electronics Engg (Diploma),Prof. Suresh Mer,Assistant Professor,M.Tech,Electronics Engineering,sureshbmer79@gmail.com,,Adhoc
Electrical / Electronics Engg (Diploma),Prof. Priyanka Pagare,Assistant Professor,M.E.,Power System,pbpagare@ee.vjti.ac.in,,Adhoc
Electrical / Electronics Engg (Diploma),Prof. Vidnya Gosavi,Adhoc Faculty,B.Tech,Electrical Engineering,vidnyagosavi124@gmail.com,,Adhoc
Computer Engineering & IT,Dr. V.B. Nikam,Associate Professor & HOD (IT),Ph.D.,"High Performance GPU Computing, BioInformatics, Data Mining, ML, Deep Learning, Cloud Computing",vbnikam@it.vjti.ac.in,022-24198150,HOD (Associate Professor)
Computer Engineering & IT,Prof. P.M. Chawan,Associate Professor (Computer Engg),M.E.,"Software Engineering, Data Mining, Machine Learning, Parallel Computing",pmchawan@ce.vjti.ac.in,,Permanent
Computer Engineering & IT,Dr. M.R. Shirole,Associate Professor (IT),Ph.D.,"Software Engg., Machine Learning, Networking, Cloud Computing",mrshirole@it.vjti.ac.in,,Associate Dean IT Infrastructure
Computer Engineering & IT,Dr. M.M. Chandane,Associate Professor (IT),Ph.D.,"Ad-hoc Network, WSN, IoT, Wireless Network Security, Pervasive Computing",mmchandane@it.vjti.ac.in,,Permanent
Computer Engineering & IT,Prof. S.C. Shrawne,Assistant Professor (Computer Engg),M.Tech,"Network & Information Security, Data Mining, Artificial Intelligence",scshrawne@ce.vjti.ac.in,,Permanent
Computer Engineering & IT,Dr. V.K. Sambhe,Assistant Professor (IT),Ph.D.,Wireless Communication,vksambhe@it.vjti.ac.in,,Permanent
Computer Engineering & IT,Dr. S.S. Udmale,Assistant Professor (IT),Ph.D.,"Machine Learning, Artificial Intelligence",ssudmale@it.vjti.ac.in,,Permanent
Computer Engineering & IT,Prof. M.U. Kulkarni,Assistant Professor (Computer Engg),M.Tech,"Machine Learning, Natural Language Processing",mukulkarni@ce.vjti.ac.in,,Permanent
Computer Engineering & IT,Dr. S.T. Shingade,Assistant Professor (IT),Ph.D.,Parallel and Distributed Computing,stshingade@it.vjti.ac.in,,Permanent
Computer Engineering & IT,Prof. K.K. Joshi,Assistant Professor (IT),M.Tech,"Network Security, Cloud Computing, Machine Learning",kkjoshi@it.vjti.ac.in,,Permanent
Computer Engineering & IT,Dr. Varshapriya N. Jyotinagar,Assistant Professor (Computer Engg),Ph.D.,"Cloud Computing, Cyber Security, Digital Forensics, Embedded Systems & IoT",varshapriyajn@ce.vjti.ac.in,,Permanent
Computer Engineering & IT,Dr. S.S. Suratkar,Assistant Professor (Computer Engg),Ph.D.,"Cyber Security, Data Mining, Database Forensics",sssuratkar@ce.vjti.ac.in,,Permanent
Computer Engineering & IT,Prof. V.D. Dhore,Assistant Professor (Computer Engg),M.Tech,"Network Security, Big Data Analytics, Machine Learning",vddhore@ce.vjti.ac.in,,Permanent
Computer Engineering & IT,Prof. S.A. Khedkar,Assistant Professor (Computer Engg),M.Tech,Computer Network & Information Security,sakhedkar@ce.vjti.ac.in,,Permanent
Computer Engineering & IT,Prof. S.S. Lachure,Assistant Professor (IT),M.Tech,"Flood Modeling, Data Science, Machine Learning, Big Data",sslachure@it.vjti.ac.in,,Permanent
Computer Engineering & IT,Dr. S.D. Kale,Assistant Professor (Computer Engg),Ph.D.,"Artificial Intelligence, Machine Learning, Text Analytics",sdkale@ce.vjti.ac.in,,Permanent
Computer Engineering & IT,Mr. Yashvant Kanetkar,Distinguished Professor of Practice,,,,,Professor of Practice
Computer Engineering & IT,Mr. Sachin Teke,Distinguished Professor of Practice,,,,,Professor of Practice
Computer Engineering & IT,Dr. Lalit Kumar Singh,Professor of Practice,Ph.D.,,,,Professor of Practice
Computer Engineering & IT,Dr. Sopan Govind Kolte,Tenure Faculty,"M.E. (Computer Engg), Ph.D.",Artificial Intelligence,sgkolte@ce.vjti.ac.in,,Tenure
Computer Engineering & IT,Dr. Noshin Abizer Sabuwala,Tenure Faculty,Ph.D.,"Communication Security, UAVs Communication, IoT",nasabuwala@ce.vjti.ac.in,,Tenure
Computer Engineering & IT,Dr. Neha Singh,Tenure Faculty,Ph.D.,,,,Tenure
Computer Engineering & IT,Prof. Pooja Kokare,Adhoc Faculty,M.Tech,Computer Engineering,pdkokare@ce.vjti.ac.in,,Adhoc
Computer Engineering & IT,Prof. Nikhil Handa,Adhoc Faculty,M.Tech,Computer Engineering,nrhanda@ce.vjti.ac.in,,Adhoc
Computer Engineering & IT,Prof. Vedashree Awati,Adhoc Faculty,M.Tech,Software Technologies,vawati@ce.vjti.ac.in,,Adhoc
Computer Engineering & IT,Prof. Dhanashri Borage,Adhoc Faculty,,,,,Adhoc
Computer Engineering & IT,Prof. Isaivani Mathiyalagan,Adhoc Faculty,,,,,Adhoc
Computer Engineering & IT,Prof. Prachi Shinde,Adhoc Faculty,M.Tech,Computer Engineering,psshinde@ce.vjti.ac.in,,Adhoc
Computer Engineering & IT,Prof. Shreekant Bedekar,Visiting Faculty,,,,,Visiting
Computer Engineering & IT,Prof. R. Santha Mario Rani,Visiting Faculty,,,,,Visiting
Textile Engineering,Dr. S.P. Borkar,Professor & HOD,Ph.D.,"Fibre Science, Textile Composites, Textile Manufacturing, Weaving, Coating & Lamination",spborkar@tx.vjti.ac.in,24198257,Professor & HOD
Textile Engineering,Dr. A.L. Bhongade,Associate Professor,Ph.D.,"Spinning, Technical Textiles, Composites Technology",albhongade@tx.vjti.ac.in,24198258,Permanent
Textile Engineering,Dr. Neha Mehra,Assistant Professor,Ph.D. (Tech.),"Nanotechnology in Textiles, Ecofriendly Pretreatment, Colouration, Chemical Finishing, Technical Textiles",nehamehra@tx.vjti.ac.in,,Permanent
Textile Engineering,Dr. Suranjana Gangopadhyay,Assistant Professor,Ph.D.,"Smart Textiles, Electrically Conductive Textiles, Manmade Fibre Production, Textile Testing & QC",sgangopadhyay@tx.vjti.ac.in,24198256,Permanent
Textile Engineering,Prof. Aniket K. Gajbhiye,Assistant Professor,M.Tech (Textile Technology),"Fabric Formation Technology, Woven Fabric Manufacturing, Knitting, Technical Textiles",akgajbhiye@tx.vjti.ac.in,,Permanent
Textile Engineering,Prof. Sanjay A. Patil,Assistant Professor,M.Tech,"Fabric Formation, Knitting, Garment Manufacturing",sapatil@tx.vjti.ac.in,24198264,Permanent
Textile Engineering,Dr. Mukesh Kumar Sinha,Professor of Practice,Ph.D.,,,,Professor of Practice
Textile Engineering,Dr. Shashank Shende,Professor of Practice,Ph.D.,,,,Professor of Practice
Textile Engineering,Dr. Manisha Hira,Tenure Faculty,Ph.D. (Textile Engg.),"Polymers, Woven Fabric Constructions, Textile Testing, Advanced Textile Materials, Costing",mahira@tx.vjti.ac.in,,Tenure
Textile Engineering,Dr. Rachana Shukla,Tenure Faculty,Ph.D. (Tech.),"Textile Processing, Fibre Science, Manmade Fibre Production, Sustainable Processing",rsshukla@tx.vjti.ac.in,,Tenure
Textile Engineering,Dr. Harwinder Singh,Tenure Faculty,"Ph.D. (Textile Technology, NIT Jalandhar)",,hsingh@tx.vjti.ac.in,,Tenure
Textile Engineering,Dr. S. Joshi,Tenure Faculty,Ph.D.,"Sustainable Manufacturing, Biopolymeric Textile Finishes, Textile Waste Recycling, Antimicrobial Textiles",sjoshi@tx.vjti.ac.in,,Tenure
Textile Engineering,Dr. Prasanta Das,Tenure Faculty,Ph.D. (Textile Technology),"Yarn Manufacturing, Fabric Manufacturing, Textile Testing, Fibre Science, Medical Textile",pdas@tx.vjti.ac.in,,Tenure
Textile Engineering,Dr. Kaustubh Chandrashekhar Patankar,Adhoc Faculty,"Ph.D. (Science) in Textile Chemistry, ICT Mumbai",Textile Chemistry,kcpatankar@tx.vjti.ac.in,,Adhoc
Textile Engineering,Mr. Bhushan Madhukar Wale,Adhoc Faculty,"B.Tech (Mechanical), M.Sc. (Mech Engg, Univ. of Hertfordshire, UK)",Mechanical and Management,bmwale@tx.vjti.ac.in,,Adhoc
Textile Engineering,Ms. Mansi Solanki,Adhoc Faculty,M.Sc. (Textile & Clothing),"Apparel, Design & Pattern Making",masolanki@tx.vjti.ac.in,,Adhoc
Textile Engineering (Diploma),Prof. S.N. Tetambe,Lecturer (Diploma HOD),"M.Tech, Pursuing Ph.D.","Fabric Manufacturing, Advanced Weaving, Garment Technology, Textile Composites",sntetambe@tx.vjti.ac.in,24198263,Diploma HOD
Textile Engineering (Diploma),Dr. A.N. Baliga,Sr. Lecturer (Selection Grade),Ph.D.,"Textile Technology, Spinning, Composites, Medical Textiles",anbaliga@tx.vjti.ac.in,24198262,Permanent Lecturer
Textile Engineering (Diploma),Dr. D.V. Raisinghani,Lecturer (Selection Grade),Ph.D.,"Fabric Manufacturing: Weaving, Knitting, Nonwoven, Technical Textiles, Geotextiles",raisinghanidv@tx.vjti.ac.in,24198261,Permanent Lecturer
Textile Engineering (Diploma),Dr. D.P. Kakad,Lecturer,Ph.D.,"Textile Testing, Maintenance Management, Marketing Management, Nano Textile",dpkakad@tx.vjti.ac.in,24198263,Permanent Lecturer
Textile Engineering (Diploma),Ms. Ishwari Vidhate,Adhoc Faculty,B.Tech,"Fabric Manufacturing, Yarn Manufacturing, Textile Chemistry",isvidhate@tx.vjti.ac.in,,Adhoc
Textile Engineering (Diploma),Rushikesh Bhimrao Shinde,Adhoc Faculty,B.Tech (Manmade Textile Technology),Manmade Textile Technology,rbshinde@tx.vjti.ac.in,,Adhoc"""

def upload_teachers():
    lines = csv_data.strip().split("\n")[1:] # Skip header
    reader = csv.reader(lines)

    count = 0
    for row in reader:
        if not row: continue
        dept = row[0]
        name = row[1]
        desig = row[2]
        qual = row[3]
        spec = row[4]
        email = row[5]
        phone = row[6]

        # Logic: Password is FirstName@123
        # Remove Dr./Mr./Mrs./Prof.
        clean_name = name.replace("Dr. ", "").replace("Mr. ", "").replace("Mrs. ", "").replace("Prof. ", "")
        first_name = clean_name.split()[0].capitalize()
        password = f"{first_name}@123"

        # Logic: Username is email prefix
        username = email.split('@')[0] if email else first_name.lower() + str(count)

        # Branch mapping
        branch = DEPT_MAP.get(dept, "Unknown")

        # User ID - Use email prefix or UUID
        user_id = username.upper()

        # Create User
        user = User(
            id=user_id,
            username=username,
            email=email or f"{username}@vjti.ac.in",
            password_hash=password,
            full_name=name,
            role="faculty"
        )

        # Create Teacher
        teacher = Teacher(
            id=user_id,
            employee_id=user_id,
            full_name=name,
            branch=branch,
            designation=desig,
            qualification=qual,
            specialization=spec,
            phone=phone
        )

        try:
            db.add(user)
            db.flush()
            db.add(teacher)
            db.commit()
            count += 1
            print(f"Added: {name} ({username})")
        except Exception as e:
            db.rollback()
            print(f"Failed to add {name}: {e}")

    print(f"\nDone! Successfully added {count} faculty members.")

if __name__ == "__main__":
    upload_teachers()
